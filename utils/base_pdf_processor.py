__all__ = ['BasePDFProcessor', 'BaseDataPos']

from collections import defaultdict
from pydantic import BaseModel
import pdfplumber

# ===============================================
# =============== Data Models ===================
# ===============================================

class BaseDataPos(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float


class Axis(BaseModel):
    x: str = 'x'
    y: str = 'y'

all_shippers = ["shadowfax", "amazon"]

# ===============================================
# =============== PDF Processor =================
# ===============================================

class BasePDFProcessor:
    def __init__(self, pdf_path_or_pdf_bytes: str | bytes):
        self.__pdf_path = pdf_path_or_pdf_bytes
        self.pdf_words, self.pdf_width, self.pdf_height  = self.__get_pdf_data__()

    def __get_pdf_data__(self):
        with pdfplumber.open(self.__pdf_path) as pdf:
            pdf_words = []
            pdf_width = pdf.pages[0].width
            pdf_height = pdf.pages[0].height
            for page in pdf.pages:
                page_words = page.extract_words()
                pdf_words.extend(page_words)
            return pdf_words, pdf_width, pdf_height

    def __pdf_pos__(self, axis:Axis, percentage:float):
        if axis == Axis().x:
            return self.pdf_width * percentage / 100
        elif axis == Axis().y:
            return self.pdf_height * percentage / 100
        else:
            raise ValueError(f"Invalid axis: {axis}")

    def __extract_box_data_from(self, data_pos: BaseDataPos):
        x0 = self.__pdf_pos__(Axis().x, data_pos.x1)
        x1 = self.__pdf_pos__(Axis().x, data_pos.x2)
        y0 = self.__pdf_pos__(Axis().y, data_pos.y1)
        y1 = self.__pdf_pos__(Axis().y, data_pos.y2)

        box_words = [
            word for word in self.pdf_words
            if x0 <= float(word['x0']) <= x1 and y0 <= float(word['top']) <= y1
        ]

        lines = defaultdict(list)
        y_tol = 2  # adjust for precision vs robustness
        for word in box_words:
            y_key = round(word['top'] / y_tol) * y_tol
            lines[y_key].append(word)

        sorted_lines = []
        for y in sorted(lines.keys()):
            line_words = sorted(lines[y], key=lambda w: w['x0'])
            line_text = " ".join(w['text'] for w in line_words)
            sorted_lines.append(line_text)

        return "\n".join(sorted_lines)

    def get_label_shipper(self):
        for block in self.pdf_words:
            for shipper in all_shippers:
                if shipper.lower() in block['text'].lower():
                    return shipper
        raise ValueError("No label shipper detected")

    def get_word_position(self, search_text: str, occurrence: int = 1) -> BaseDataPos:
        """
            Find the position of a word or phrase in percentage coordinates.
            
            Args:
                search_text: The text to search for (case-insensitive)
                occurrence: Which occurrence to find (1-based indexing)
                
            Returns:
                BaseDataPos with percentage coordinates of the word's bounding box
                
            Raises:
                ValueError: If the text is not found or occurrence is invalid
        """
        matching_words = []
        for word in self.pdf_words:
            if search_text in word['text']:
                matching_words.append(word)
        if not matching_words:
            raise ValueError(f"Text '{search_text}' not found in PDF")
        
        if occurrence < 1 or occurrence > len(matching_words):
            raise ValueError(f"Occurrence {occurrence} not found. Found {len(matching_words)} occurrences.")
        
        target_word = matching_words[occurrence - 1]
        
        x1_percent = (float(target_word['x0']) / self.pdf_width) * 100
        x2_percent = (float(target_word['x1']) / self.pdf_width) * 100
        y1_percent = (float(target_word['top']) / self.pdf_height) * 100
        y2_percent = (float(target_word['bottom']) / self.pdf_height) * 100
        
        return BaseDataPos(
            x1=x1_percent,
            x2=x2_percent,
            y1=y1_percent,
            y2=y2_percent
        )

    def extract_data(self, data_pos: BaseDataPos):
        data_dict = {}
        print("-"*100)
        for field_name, data in data_pos.model_dump().items():
            data_pos_obj = BaseDataPos(**data)
            data_text = self.__extract_box_data_from(data_pos_obj)
            data_dict[field_name] = data_text
            print(f"{field_name}: {data_text}")
            print("-"*100)
        print('\n\n\n')
        return data_dict

    def print_pdf_words(self, with_position: bool = False):
        for word in self.pdf_words:
            if with_position:
                print(word['text'], word['x0'], word['top'], word['x1'], word['bottom'], sep="\t")
            else:
                print(word['text'])
