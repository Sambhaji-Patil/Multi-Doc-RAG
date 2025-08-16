# ShastraDocs - LLM Handler Package

## 🚀 Overview

The ShastraDocs LLM Handler Package is a comprehensive, production-ready solution for multi-provider language model management with intelligent rate limiting, specialized processors, and automated fallback mechanisms. This package enables seamless interaction with multiple LLM providers (Groq, Gemini, OpenAI) while handling rate limits gracefully and providing specialized processing for different data types.

## 🎯 Key Benefits

### **Smart Rate Limit Handling**
- **Multi-Provider Cycling**: Automatically rotates between Groq, Gemini, and OpenAI instances
- **Intelligent Cooldown Management**: Tracks rate limits per provider and implements automatic cooldowns
- **Cost-Effective Operations**: Process 200+ questions through RAG pipeline with **$0** using free tier rotation
- **Zero Downtime**: Seamless fallback between providers ensures continuous operation

### **Specialized Handlers for Specific Tasks**
- **Modular Architecture**: Choose optimal models, prompts, and formatting per data type
- **Task-Specific Optimization**: Dedicated processors for images, tables, documents, and general text
- **Provider Flexibility**: Run with single API key or multiple keys across different providers

### **Production-Ready Features**
- **Async/Await Support**: Full FastAPI compatibility for high-performance applications
- **Error Recovery**: Robust exception handling with automatic retries
- **Comprehensive Logging**: Detailed status tracking and performance monitoring
- **Thread-Safe Operations**: Concurrent request handling with proper synchronization


### Error Handling

Comprehensive error handling with:

- **Automatic Retries**: Built-in retry logic for transient failures
- **Provider Fallback**: Seamless switching between providers
- **Graceful Degradation**: Continues operation even with partial failures
- **Detailed Logging**: Comprehensive error tracking and reporting

## 📊 Performance Metrics

### Cost Efficiency
- **Free Tier Optimization**: 200+ questions processed at $0 cost
- **Smart Provider Selection**: Chooses most cost-effective available provider
- **Rate Limit Avoidance**: Prevents unnecessary paid API calls

### Response Times
- **Concurrent Processing**: Multiple requests handled simultaneously
- **Provider Optimization**: Fastest available provider selected first
- **Caching Support**: LRU cache for frequently used configurations

### Reliability
- **99%+ Uptime**: Multiple provider fallback ensures availability
- **Error Recovery**: Automatic recovery from rate limits and failures
- **Status Monitoring**: Real-time health checking of all providers


## 📦 Package Components

### 🔧 Core Components

#### **1. Unified LLM Handler (`llm_handler.py`)**

The heart of the package - a sophisticated multi-provider LLM manager with intelligent routing and rate limit handling.

**Key Features:**
- **Multi-Instance Support**: Handle multiple API keys per provider
- **Priority-Based Routing**: Groq → Gemini → OpenAI fallback sequence  
- **Automatic Cooldown Management**: 60-second cooldowns for rate-limited providers
- **Real-Time Status Tracking**: Monitor provider availability and performance
- **Reasoning Model Support**: Special handling for reasoning models with format options

**Usage Example:**
```python
from llm_handler import llm_handler

# Generate text with automatic provider selection
result, provider, instance = await llm_handler.generate_text(
    system_prompt="You are a helpful assistant",
    user_prompt="Explain quantum computing",
    temperature=0.7,
    reasoning_format="hidden"  # For reasoning models
)

# Get provider status
status = llm_handler.get_provider_status()
print(f"Active providers: {len(status)}")

# Reset cooldowns if needed
llm_handler.reset_cooldowns()
```

**Supported Providers:**
- **Groq**: High-speed inference with reasoning model support
- **Gemini**: Google's advanced models with vision capabilities  
- **OpenAI**: GPT models with reliable performance


### Refer Confiugration section to learn more on how to setupp api keys
-----
#### **2. OneShot QA System (`one_shotter.py`)**

An advanced question-answering system that combines context analysis, web scraping, and search capabilities for comprehensive responses.

**Key Features:**
- **Intelligent Content Strategy**: Automatically determines need for additional information
- **Multi-Source Integration**: Combines provided context with scraped web content
- **Smart URL Detection**: Extracts and validates URLs from context and questions
- **Async Web Scraping**: High-performance concurrent scraping with rate limiting
- **Enhanced Answer Generation**: Utilizes all available sources for comprehensive responses

**Workflow Process:**
1. **URL Extraction**: Identifies relevant links in context/questions
2. **Content Strategy**: Determines if additional information is needed
3. **Web Scraping**: Fetches content from identified URLs
4. **Context Integration**: Combines original context with scraped content
5. **Answer Generation**: Produces comprehensive responses using all sources

**Usage Example:**
```python
from one_shotter import get_oneshot_answer

# Comprehensive QA with automatic content enhancement
questions = [
    "What are the latest developments in AI?",
    "How do quantum computers work?"
]

context = """
AI has been advancing rapidly... 
Check out: https://openai.com/research
"""

answers = await get_oneshot_answer(context, questions)
# Returns detailed answers incorporating scraped web content
```

### 🎯 Specialized Handlers

#### **3. Image Analysis Handler (`image_answerer.py`)**

Specialized processor for visual question answering using Gemini's vision capabilities.

**Features:**
- **Multi-Format Support**: URLs and local file paths
- **Structured Responses**: Numbered, detailed explanations
- **Retry Logic**: Automatic retries with error handling
- **Image Preprocessing**: Automatic RGB conversion and validation

**Usage Example:**
```python
from image_answerer import get_answer_for_image

questions = [
    "What objects are in this image?",
    "What is the dominant color scheme?"
]

answers = get_answer_for_image(
    "https://example.com/image.jpg", 
    questions,
    retries=3
)
```

#### **4. Tabular Data Handler (`tabular_answer.py`)**

Optimized for analyzing structured data with batch processing capabilities.

**Features:**
- **Batch Processing**: Handle multiple questions efficiently
- **Structured Parsing**: Robust numbered response extraction
- **Data Validation**: Handles malicious instructions and missing data
- **Performance Optimization**: Configurable batch sizes

**Usage Example:**
```python
from tabular_answer import get_answer_for_tabluar

data = """
| Product | Sales | Region |
|---------|-------|--------|
| A       | 1000  | North  |
| B       | 1500  | South  |
"""

questions = [
    "Which product has highest sales?",
    "What is the total sales?"
]

answers = get_answer_for_tabluar(data, questions, batch_size=10)
```

#### **5. Lite LLM Handler (`lite_llm.py`)**

Lightweight handler for simple, fast responses with minimal overhead.

**Features:**
- **Single Provider**: Focused Groq integration
- **Minimal Configuration**: Simple prompt-to-response interface
- **High Performance**: Optimized for speed over complex features
- **Configurable Parameters**: Adjustable temperature and token limits

## ⚙️ Configuration Setup

### Environment Variables Setup

The package uses a flexible configuration system that automatically detects and loads multiple API keys for each provider. Create a `.env` file with your API keys using the following naming convention:

#### **Basic Configuration (.env file)**

```bash
# === GROQ PROVIDER ===
# Multiple Groq API Keys (detects GROQ_API_KEY_1 through GROQ_API_KEY_10)
GROQ_API_KEY_1=your_first_groq_key_here
GROQ_API_KEY_2=your_second_groq_key_here
GROQ_API_KEY_3=your_third_groq_key_here
# Add more as needed: GROQ_API_KEY_4, GROQ_API_KEY_5, etc.

# Optional: Custom models per Groq instance (defaults to qwen/qwen3-32b)
DEFAULT_GROQ_MODEL=qwen/qwen3-32b
GROQ_MODEL_1=llama3-70b-8192
GROQ_MODEL_2=mixtral-8x7b-32768
# GROQ_MODEL_3 will use DEFAULT_GROQ_MODEL if not specified

# === GEMINI PROVIDER ===
# Multiple Gemini API Keys (detects GEMINI_API_KEY_1 through GEMINI_API_KEY_10)  
GEMINI_API_KEY_1=your_first_gemini_key_here
GEMINI_API_KEY_2=your_second_gemini_key_here
GEMINI_API_KEY_3=your_third_gemini_key_here
# Add more as needed: GEMINI_API_KEY_4, GEMINI_API_KEY_5, etc.

# Optional: Custom models per Gemini instance (defaults to gemini-2.0-flash)
DEFAULT_GEMINI_MODEL=gemini-2.0-flash
GEMINI_MODEL_1=gemini-1.5-pro
GEMINI_MODEL_2=gemini-2.0-flash
# GEMINI_MODEL_3 will use DEFAULT_GEMINI_MODEL if not specified

# === OPENAI PROVIDER ===
# Multiple OpenAI API Keys (detects OPENAI_API_KEY_1 through OPENAI_API_KEY_10)
OPENAI_API_KEY_1=your_first_openai_key_here
OPENAI_API_KEY_2=your_second_openai_key_here
# Add more as needed: OPENAI_API_KEY_3, OPENAI_API_KEY_4, etc.

# Optional: Custom models per OpenAI instance (defaults to gpt-4o-mini)
DEFAULT_OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL_1=gpt-4o
OPENAI_MODEL_2=gpt-4-turbo
# OPENAI_MODEL_3 will use DEFAULT_OPENAI_MODEL if not specified

# === SPECIALIZED HANDLERS ===
# For specific handlers that need dedicated keys
GROQ_API_KEY_LITE=your_groq_key_for_lite_handler
GROQ_API_KEY_TABULAR=your_groq_key_for_tabular_handler
GEMINI_API_KEY_IMAGE=your_gemini_key_for_image_handler

# === GLOBAL DEFAULTS ===
MAX_TOKENS=2048
TEMPERATURE=0.7
```

### **Quick Setup Guide**

1. **Create `.env` file** in your project root
2. **Add API keys** using the `PROVIDER_API_KEY_NUMBER` format
3. **Set default models** (optional) using `DEFAULT_PROVIDER_MODEL`
4. **Customize specific models** (optional) using `PROVIDER_MODEL_NUMBER`
5. **Run your application** - the handler will auto-detect all configurations


## 🚀 Quick Start

### Basic Installation

```bash
pip install -r requirements.txt
```

### Required Dependencies

```
groq
google-generativeai
openai
langchain-groq
langchain-google-genai
httpx
beautifulsoup4
pydantic
python-dotenv
```

### Simple Usage

```python
import asyncio
from llm_handler import llm_handler
from one_shotter import get_oneshot_answer

async def main():
    # Simple text generation
    result, provider, instance = await llm_handler.generate_text(
        system_prompt="You are a helpful assistant",
        user_prompt="Explain machine learning in simple terms"
    )
    print(f"Generated by {provider} ({instance}): {result}")
    
    # Advanced QA with content enhancement
    context = "Machine learning is a subset of AI..."
    questions = ["What are the main types of ML?"]
    
    answers = await get_oneshot_answer(context, questions)
    print(f"Enhanced answer: {answers[0]}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔍 Advanced Features

### Rate Limit Management

The package automatically handles rate limits through:

- **Provider Cycling**: Rotates between available instances
- **Cooldown Tracking**: Monitors rate limit windows per provider
- **Automatic Recovery**: Restores providers when cooldowns expire
- **Status Monitoring**: Real-time availability tracking

### FastAPI Integration

Full async/await support for FastAPI applications:

```python
from fastapi import FastAPI
from one_shotter import get_oneshot_answer

app = FastAPI()

@app.post("/qa")
async def question_answer(context: str, questions: list[str]):
    answers = await get_oneshot_answer(context, questions)
    return {"answers": answers}
```

### Error Handling

Comprehensive error handling with:

- **Automatic Retries**: Built-in retry logic for transient failures
- **Provider Fallback**: Seamless switching between providers
- **Graceful Degradation**: Continues operation even with partial failures
- **Detailed Logging**: Comprehensive error tracking and reporting

## 📊 Performance Metrics

### Cost Efficiency
- **Free Tier Optimization**: 200+ questions processed at $0 cost
- **Smart Provider Selection**: Chooses most cost-effective available provider
- **Rate Limit Avoidance**: Prevents unnecessary paid API calls

### Response Times
- **Concurrent Processing**: Multiple requests handled simultaneously
- **Provider Optimization**: Fastest available provider selected first
- **Caching Support**: LRU cache for frequently used configurations

### Reliability
- **99%+ Uptime**: Multiple provider fallback ensures availability
- **Error Recovery**: Automatic recovery from rate limits and failures
- **Status Monitoring**: Real-time health checking of all providers

## 🛠️ Troubleshooting

### Common Issues

1. **No Providers Available**
   - Check API key configuration
   - Verify network connectivity
   - Review provider status with `get_provider_status()`

2. **Rate Limit Errors**
   - Monitor cooldown status
   - Add more API keys to configuration
   - Use `reset_cooldowns()` for testing

3. **Scraping Failures**
   - Check URL accessibility
   - Verify network firewall settings
   - Review timeout configurations

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed provider information
info = llm_handler.get_provider_info()
print(json.dumps(info, indent=2))
```

## 🤝 Contributing

This package is part of the larger ShastraDocs project. For contributions:

1. Follow the modular architecture pattern
2. Maintain async/await compatibility
3. Add comprehensive error handling
4. Include type hints and documentation
5. Test with multiple providers

## 📄 License

Part of the ShastraDocs project. Refer to the main project license for terms and conditions.