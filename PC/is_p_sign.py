#is_p_sign.py

import pytesseract
import cv2
import numpy as np

# 윈도우 환경이라면 Tesseract 실행 경로 지정 필요
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def is_p_sign(image):
    """
    입력된 이진 이미지나 전처리된 이미지에서 'P' 문자를 인식하는 함수.
    이미지 크기: (28, 28) 또는 (64, 64) 권장.
    """
    # 전처리: 너무 작은 건 확장
    resized = cv2.resize(image, (64, 64))

    # Tesseract OCR을 이용해 텍스트 추출
    config = '--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    text = pytesseract.image_to_string(resized, config=config)

    print("OCR 결과:", text.strip())

    # 'P'가 인식되었는지 확인
    return 'P' in text.upper()
