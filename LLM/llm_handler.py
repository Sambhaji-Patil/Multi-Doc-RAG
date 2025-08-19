"""
Unified LLM Handler with Multiple Provider Instances
Supports multiple Groq, Gemini, and OpenAI instances with different API keys.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import openai
import google.generativeai as genai
from groq import Groq
from config.config import get_provider_configs, MAX_TOKENS, TEMPERATURE

from datetime import datetime
from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)

class ProviderType(Enum):
    """Enum for LLM provider types."""
    GROQ = "groq"
    GEMINI = "gemini"
    OPENAI = "openai"


@dataclass
class ProviderInstance:
    """Represents a single provider instance."""
    provider_type: ProviderType
    instance_name: str
    client: Any
    model: str
    api_key: str


@dataclass
class ProviderStatus:
    """Tracks provider instance status and cooldown."""
    is_available: bool = True
    cooldown_until: float = 0.0
    error_count: int = 0
    last_success: float = 0.0


class UnifiedLLMHandler:
    """Unified handler supporting multiple instances of each LLM provider."""
    
    def __init__(self):
        """Initialize the LLM handler with all configured provider instances."""
        self.provider_instances: Dict[str, ProviderInstance] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}
        self.cooldown_duration = 60.0  # 1 minute cooldown
        
        # Priority order: Groq instances first, then Gemini, then OpenAI
        self.provider_priority: List[str] = []
        
        # Initialize all available providers
        self._init_providers()
        
        if not self.provider_instances:
            raise ValueError("No LLM providers could be initialized. Check your configuration.")

        logger.info("Initialized LLM provider instances", count=len(self.provider_instances))
        self._print_provider_summary()
    
    def _init_providers(self):
        """Initialize all configured LLM provider instances."""
        provider_configs = get_provider_configs()
        
        # Initialize Groq instances
        for groq_config in provider_configs.get('groq', []):
            self._init_groq_instance(groq_config)
        
        # Initialize Gemini instances
        for gemini_config in provider_configs.get('gemini', []):
            self._init_gemini_instance(gemini_config)
        
        # Initialize OpenAI instances
        for openai_config in provider_configs.get('openai', []):
            self._init_openai_instance(openai_config)
    
    def _init_groq_instance(self, config: Dict[str, Any]):
        """Initialize a Groq instance."""
        try:
            instance_name = f"groq_{config['name']}"
            
            client = Groq(api_key=config['api_key'])
            instance = ProviderInstance(
                provider_type=ProviderType.GROQ,
                instance_name=instance_name,
                client=client,
                model=config['model'],
                api_key=config['api_key'][:8] + "..."  # Store truncated key for logging
            )
            
            self.provider_instances[instance_name] = instance
            self.provider_status[instance_name] = ProviderStatus()
            self.provider_priority.append(instance_name)
            
            logger.info("Initialized provider instance", instance=instance_name, model=config['model'])
            
        except Exception as e:
            logger.error("Failed to initialize Groq instance", name=config['name'], error=str(e))
    
    def _init_gemini_instance(self, config: Dict[str, Any]):
        """Initialize a Gemini instance."""
        try:
            instance_name = f"gemini_{config['name']}"
            
            # Create a separate genai configuration for this instance
            # Note: genai.configure is global, so we'll handle this carefully
            client = genai.GenerativeModel(config['model'])
            
            instance = ProviderInstance(
                provider_type=ProviderType.GEMINI,
                instance_name=instance_name,
                client=client,
                model=config['model'],
                api_key=config['api_key'][:8] + "..."
            )
            
            # Store the API key for later use
            instance.full_api_key = config['api_key']
            
            self.provider_instances[instance_name] = instance
            self.provider_status[instance_name] = ProviderStatus()
            self.provider_priority.append(instance_name)
            
            logger.info("Initialized provider instance", instance=instance_name, model=config['model'])
            
        except Exception as e:
            logger.error("Failed to initialize Gemini instance", name=config['name'], error=str(e))
    
    def _init_openai_instance(self, config: Dict[str, Any]):
        """Initialize an OpenAI instance."""
        try:
            instance_name = f"openai_{config['name']}"
            
            # Create OpenAI client instance
            client = openai.OpenAI(api_key=config['api_key'])
            
            instance = ProviderInstance(
                provider_type=ProviderType.OPENAI,
                instance_name=instance_name,
                client=client,
                model=config['model'],
                api_key=config['api_key'][:8] + "..."
            )
            
            self.provider_instances[instance_name] = instance
            self.provider_status[instance_name] = ProviderStatus()
            self.provider_priority.append(instance_name)
            
            logger.info("Initialized provider instance", instance=instance_name, model=config['model'])
            
        except Exception as e:
            logger.error("Failed to initialize OpenAI instance", name=config['name'], error=str(e))
    
    def _print_provider_summary(self):
        """Log a summary of initialized providers once."""
        provider_counts = {}
        for instance in self.provider_instances.values():
            provider_type = instance.provider_type.value
            provider_counts[provider_type] = provider_counts.get(provider_type, 0) + 1
        logger.info("Provider summary", summary=provider_counts, total=len(self.provider_instances))
    
    def _get_available_provider(self) -> Optional[str]:
        """Get the next available provider instance based on priority and cooldowns."""
        current_time = time.time()
        
        # Check each provider in priority order
        for instance_name in self.provider_priority:
            if instance_name not in self.provider_instances:
                continue
            
            status = self.provider_status[instance_name]
            
            # Check if cooldown has expired
            if not status.is_available and current_time >= status.cooldown_until:
                status.is_available = True
                status.error_count = 0
                logger.info("Instance cooldown expired", instance=instance_name)
            
            # Return first available provider
            if status.is_available:
                return instance_name
        
        return None
    
    def _handle_rate_limit(self, instance_name: str, error: Exception):
        """Handle rate limit by putting provider instance on cooldown."""
        current_time = time.time()
        status = self.provider_status[instance_name]
        
        # Check if this is a rate limit error
        error_str = str(error).lower()
        is_rate_limit = any(keyword in error_str for keyword in [
            'rate limit', 'quota', 'too many requests', '429', 'ratelimit'
        ])
        
        if is_rate_limit:
            status.is_available = False
            status.cooldown_until = current_time + self.cooldown_duration
            status.error_count += 1

            logger.warning("Instance hit rate limit", instance=instance_name, cooldown_until=time.strftime('%H:%M:%S', time.localtime(status.cooldown_until)))
            return True
        
        return False
    
    async def generate_text(self, 
                          system_prompt: str, 
                          user_prompt: str, 
                          temperature: Optional[float] = None,
                          max_tokens: Optional[int] = None,
                          reasoning_format: str = "hidden") -> Dict[str, Any]:
        """

        Generate text using available LLM provider instances with automatic fallback.
        
        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User query/prompt
            temperature: Sampling temperature (uses config default if None)
            max_tokens: Maximum tokens to generate (uses config default if None)
            reasoning_format: For reasoning models - "hidden" (default), "raw", or "parsed"
            
        Returns:
            Dictionary with 'text', 'provider', 'instance', and 'model' keys
        """
        
        # Optional debug logging - create directory if it doesn't exist
        try:
            import os
            os.makedirs("test/context", exist_ok=True)
            with open(f"test/context/{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w') as f:
                f.write(user_prompt)
        except Exception as e:
            # Silently continue if debug logging fails
            pass

        temp = temperature if temperature is not None else TEMPERATURE
        max_tok = max_tokens if max_tokens is not None else MAX_TOKENS
        
        last_error = None
        
        # Try each available provider instance
        for attempt in range(len(self.provider_instances)):
            instance_name = self._get_available_provider()
            
            if instance_name is None:
                # All providers are on cooldown
                available_times = [
                    status.cooldown_until
                    for status in self.provider_status.values()
                    if not status.is_available
                ]
                
                if available_times:
                    min_cooldown = min(available_times) - time.time()
                    if min_cooldown > 0:
                        logger.info("All providers on cooldown, waiting", wait_seconds=round(min_cooldown, 1))
                        await asyncio.sleep(min(min_cooldown, 5))  # Wait max 5 seconds
                        continue
                break
            
            instance = self.provider_instances[instance_name]
            
            try:
                logger.info("Attempting generation", instance=instance_name, model=instance.model)
                
                if instance.provider_type == ProviderType.GROQ:
                    result = await self._generate_groq(instance, system_prompt, user_prompt, temp, max_tok, reasoning_format)
                elif instance.provider_type == ProviderType.GEMINI:
                    result = await self._generate_gemini(instance, system_prompt, user_prompt, temp, max_tok)
                elif instance.provider_type == ProviderType.OPENAI:
                    result = await self._generate_openai(instance, system_prompt, user_prompt, temp, max_tok)
                
                # Mark success
                self.provider_status[instance_name].last_success = time.time()
                
                return result, instance.provider_type.value, instance_name
                
            except Exception as e:
                logger.error("Provider instance error", instance=instance_name, error=str(e))
                last_error = e
                
                # Handle rate limiting
                if self._handle_rate_limit(instance_name, e):
                    continue  # Try next provider
                else:
                    await asyncio.sleep(1)
                    continue
        
        raise Exception(f"All LLM provider instances failed. Last error: {last_error}")
    
    async def _generate_groq(self, instance: ProviderInstance, system_prompt: str, user_prompt: str,
                           temperature: float, max_tokens: int, reasoning_format: str = "hidden") -> str:
        """Generate text using Groq with reasoning format support."""
        
        request_params = {
            "model": instance.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add reasoning_format for reasoning models
        reasoning_models = [
            "qwen/qwen3-32b"
        ]
        
        if any(model in instance.model.lower() for model in reasoning_models):
            request_params["reasoning_format"] = reasoning_format
            logger.info("Using reasoning format", format=reasoning_format)
        
        response = await asyncio.to_thread(
            instance.client.chat.completions.create,
            **request_params
        )
        
        # Handle different response formats
        if hasattr(response.choices[0].message, 'reasoning') and reasoning_format == "parsed":
            # For parsed format, reasoning is in a separate field
            reasoning = response.choices[0].message.reasoning or ""
            content = response.choices[0].message.content or ""
            
            if reasoning and reasoning_format != "hidden":
                return f"Reasoning: {reasoning}\n\nAnswer: {content}"
            else:
                return content
        else:
            # For raw and hidden formats, content contains everything or just the answer
            return response.choices[0].message.content
    
    async def _generate_gemini(self, instance: ProviderInstance, system_prompt: str, user_prompt: str,
                             temperature: float, max_tokens: int) -> str:
        """Generate text using Gemini."""
        # Configure API key for this specific request
        genai.configure(api_key=instance.full_api_key)
        
        # Combine system and user prompts for Gemini
        combined_prompt = f"{system_prompt}\n\nUser Query: {user_prompt}"
        
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # Generate response
        response = await asyncio.to_thread(
            instance.client.generate_content,
            combined_prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    async def _generate_openai(self, instance: ProviderInstance, system_prompt: str, user_prompt: str,
                             temperature: float, max_tokens: int) -> str:
        """Generate text using OpenAI."""
        response = await asyncio.to_thread(
            instance.client.chat.completions.create,
            model=instance.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    async def generate_simple(self, prompt: str,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            reasoning_format: str = "hidden") -> Dict[str, Any]:
        """
        Generate text with a simple prompt (no system message).
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            reasoning_format: For reasoning models - "hidden" (default), "raw", or "parsed"
            
        Returns:
            Dictionary with 'text', 'provider', 'instance', and 'model' keys
        """
        return await self.generate_text("", prompt, temperature, max_tokens, reasoning_format)
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all provider instances."""
        current_time = time.time()
        status_info = {}
        
        for instance_name, instance in self.provider_instances.items():
            status = self.provider_status[instance_name]
            cooldown_remaining = max(0, status.cooldown_until - current_time)
            
            status_info[instance_name] = {
                "provider_type": instance.provider_type.value,
                "model": instance.model,
                "available": status.is_available,
                "cooldown_remaining_seconds": cooldown_remaining,
                "error_count": status.error_count,
                "last_success": status.last_success,
                "last_success_ago": current_time - status.last_success if status.last_success > 0 else None,
                "api_key": instance.api_key  # Truncated version
            }
        
        return status_info
    
    def reset_cooldowns(self):
        """Reset all provider instance cooldowns."""
        for status in self.provider_status.values():
            status.is_available = True
            status.cooldown_until = 0.0
            status.error_count = 0
    logger.info("All provider instance cooldowns reset")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all configured provider instances."""
        provider_summary = {}
        for instance_name, instance in self.provider_instances.items():
            provider_type = instance.provider_type.value
            if provider_type not in provider_summary:
                provider_summary[provider_type] = []
            provider_summary[provider_type].append({
                "instance_name": instance_name,
                "model": instance.model,
                "api_key": instance.api_key
            })
        
        return {
            "total_instances": len(self.provider_instances),
            "provider_summary": provider_summary,
            "provider_priority": self.provider_priority,
            "cooldown_duration_seconds": self.cooldown_duration,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "provider_status": self.get_provider_status()
        }


# Global instance
llm_handler = UnifiedLLMHandler()