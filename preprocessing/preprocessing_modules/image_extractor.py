import cv2
import pytesseract
import numpy as np
import pandas as pd
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

def load_local_image(path: str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def sort_contours(cnts, method="top-to-bottom"):
    reverse = False
    i = 1 if method == "top-to-bottom" or method == "bottom-to-top" else 0
    if method == "right-to-left" or method == "bottom-to-top":
        reverse = True
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
                                        key=lambda b: b[1][i], reverse=reverse))
    return cnts, boundingBoxes

from collections import Counter

def extract_cells_from_grid(table_img: np.ndarray) -> pd.DataFrame:
    gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(~gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # Detect horizontal lines
    horizontal = binary.copy()
    cols = horizontal.shape[1]
    horizontal_size = cols // 15
    horizontal_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
    horizontal = cv2.erode(horizontal, horizontal_structure)
    horizontal = cv2.dilate(horizontal, horizontal_structure)

    # Detect vertical lines
    vertical = binary.copy()
    rows = vertical.shape[0]
    vertical_size = rows // 15
    vertical_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
    vertical = cv2.erode(vertical, vertical_structure)
    vertical = cv2.dilate(vertical, vertical_structure)

    # Combine mask
    mask = cv2.add(horizontal, vertical)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    cells = []
# Inside loop over contours
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        
        # NEW: filter out garbage boxes (lines, dash artifacts, etc.)
        if w < 20 or h < 20:
            continue  # noise
        
        # Heuristic: skip cell if mostly empty image (white)
        roi = table_img[y:y+h, x:x+w]
        white_ratio = cv2.countNonZero(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)) / (w * h + 1e-5)
        if white_ratio < 0.05:  # >95% empty
            continue
        
        cells.append((x, y, w, h))


    if not cells:
        return pd.DataFrame()

    # Sort top-to-bottom
    cells = sorted(cells, key=lambda b: (b[1], b[0]))

    # Group by row using y-coordinate proximity
    row_tolerance = 15
    rows = []
    current_row = []
    last_y = None

    for cell in cells:
        x, y, w, h = cell
        if last_y is None or abs(y - last_y) <= row_tolerance:
            current_row.append(cell)
        else:
            rows.append(sorted(current_row, key=lambda b: b[0]))
            current_row = [cell]
        last_y = y
    if current_row:
        rows.append(sorted(current_row, key=lambda b: b[0]))

    # Determine most common number of columns (mode)
    col_counts = [len(r) for r in rows]
    if not col_counts:
        return pd.DataFrame()
    most_common_cols = Counter(col_counts).most_common(1)[0][0]

    # Extract text
    table_data = []
    for row in rows:
        sorted_row = sorted(row, key=lambda b: b[0])
        row_data = []
        for x, y, w, h in sorted_row:
            cell_img = table_img[y:y+h, x:x+w]
            cell_text = pytesseract.image_to_string(cell_img, config="--psm 7").strip()
            row_data.append(cell_text)
        # Adjust row length to match majority column count
        if len(row_data) < most_common_cols:
            row_data += [""] * (most_common_cols - len(row_data))
        elif len(row_data) > most_common_cols:
            row_data = row_data[:most_common_cols]
        table_data.append(row_data)

    return pd.DataFrame(table_data)


def detect_table_boxes(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(~gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    horizontal = binary.copy()
    cols = horizontal.shape[1]
    horizontalsize = cols // 15
    horizontalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontalsize, 1))
    horizontal = cv2.erode(horizontal, horizontalStructure)
    horizontal = cv2.dilate(horizontal, horizontalStructure)

    vertical = binary.copy()
    rows = vertical.shape[0]
    verticalsize = rows // 15
    verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, verticalsize))
    vertical = cv2.erode(vertical, verticalStructure)
    vertical = cv2.dilate(vertical, verticalStructure)

    mask = horizontal + vertical
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 100 and h > 50:
            boxes.append((x, y, w, h))
    return boxes

def extract_non_table_text(image: np.ndarray, table_boxes: list[tuple]) -> str:
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for x, y, w, h in table_boxes:
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

    inverse_mask = cv2.bitwise_not(mask)
    non_table_img = cv2.bitwise_and(image, image, mask=inverse_mask)

    gray = cv2.cvtColor(non_table_img, cv2.COLOR_BGR2GRAY)
    custom_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(gray, config=custom_config)

def dataframe_to_markdown(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)

def extract_image(filepath: str) -> str:
    image = load_local_image(filepath)
    table_boxes = detect_table_boxes(image)

    tables = []
    for i, (x, y, w, h) in enumerate(table_boxes):
        cropped = image[y:y+h, x:x+w]
        try:
            df = extract_cells_from_grid(cropped)
            tables.append((df, (x, y, w, h)))
        except Exception as e:
            print(f"[Warning] Skipping table {i} due to error: {e}")

    non_table_text = extract_non_table_text(image, table_boxes)

    output = ""
    if non_table_text.strip():
        output += f"### Non-Table Text:\n{non_table_text.strip()}\n\n"

    for i, (df, _) in enumerate(tables):
        output += f"### Table {i+1} (Markdown):\n{dataframe_to_markdown(df)}\n\n"

    return output.strip()

