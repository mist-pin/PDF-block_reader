from utils.base_pdf_processor import BasePDFProcessor, BaseDataPos
from pydantic import BaseModel
import json


class ShadowfaxDataPos(BaseModel):
    customer_address_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)
    return_address_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)
    product_details_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)
    bill_to_or_ship_to_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)
    order_details_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)
    bill_block: BaseDataPos  = BaseDataPos(x1=0, x2=1, y1=0, y2=0)


class ReturnModel(BaseModel):
    gst_no: str




class ShadowfaxPDFProcessor(BasePDFProcessor):
    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.data_pos = self.setup_data_pos()
        self.data_dict = self.extract_data(self.data_pos)
        self.result = {
            "customer_address":self.extract_customer_address(),
            "product_details":self.extract_product_details(),
            "order_details":self.extract_order_details_block(),
            "bill_details":self.extract_bill_details(),
        }

    def setup_data_pos(self):
        customer_address_block = self.get_word_position("Customer")
        return_address_block = self.get_word_position("return")
        product_details_block = self.get_word_position("Product")
        bill_to_or_ship_to_block = self.get_word_position("SHIP")
        sold_by_block = self.get_word_position("Sold")
        description_block = self.get_word_position("Description")
        total_block = self.get_word_position("Total", 2)

        shadowfax_data_pos = ShadowfaxDataPos()
        shadowfax_data_pos.customer_address_block = BaseDataPos(
            x1=customer_address_block.x1,
            x2=40,
            y1=customer_address_block.y1,
            y2=return_address_block.y1-1
        )
        shadowfax_data_pos.return_address_block = BaseDataPos(
            x1=return_address_block.x1,
            x2=40,
            y1=return_address_block.y1,
            y2=product_details_block.y1-1
        )
        shadowfax_data_pos.product_details_block = BaseDataPos(
            x1=product_details_block.x1 -1,
            x2=100,
            y1=product_details_block.y1,
            y2=bill_to_or_ship_to_block.y1-1
        )
        shadowfax_data_pos.bill_to_or_ship_to_block = BaseDataPos(
            x1=bill_to_or_ship_to_block.x1,
            x2=sold_by_block.x1,
            y1=bill_to_or_ship_to_block.y1,
            y2=description_block.y1-1
        )
        shadowfax_data_pos.order_details_block = BaseDataPos(
            x1=sold_by_block.x1,
            x2=100,
            y1=sold_by_block.y1,
            y2=description_block.y1-1
        )
        shadowfax_data_pos.bill_block = BaseDataPos(
            x1=description_block.x1,
            x2=100,
            y1=description_block.y1-1,
            y2=total_block.y2+1
        )
        return shadowfax_data_pos

    def extract_customer_address(self):
        data = self.data_dict.get('customer_address_block')
        data = data.split('\n')
        city, state, pin = data[-1].split(',')
        result =  {
            "name":data[1],
            "address" : " ".join(data[2:-1]),
            "city" : city, 
            "state": state,
            "pin" : pin
        }
        return result

    def extract_product_details(self):
        data = self.data_dict.get('product_details_block')
        data = data.split('\n')
        # print(data, sep='\n')
        result = []
        for item in data[2:-2]:
            item = item.split(' ')
            items = {
                "sku":item[0],
                "size":item[1],
                "qty":item[2],
                "order_no":item[-1]
            }
            result.append(items)
        return result

    def extract_order_details_block(self):
        data = self.data_dict.get('order_details_block')
        data = data.split('\n')
        invoice_no, order_date, invoice_date  = data[-1].split(' ')[1:]
        result = {
            "order_date":order_date,
            "invoice_date":invoice_date,
            'invoice_no':invoice_no,
            "gst_no":data[-3].split('-')[1].strip(),
        }
        return result

    def extract_bill_details(self):
        data = self.data_dict.get('bill_block')
        data = data.split('\n')
        raw_entries = [data[x:x+3] for x in range(1, len(data[1:-1]), 3)]
        raw_total = data[-1]
        # print(raw_entries, "\n\n\n",  raw_total, sep='\n')
        result = []
        for entry in raw_entries:
            price = {
                'sgst':entry[0].split('Rs.')[1].strip(),
                'gross_amount':entry[1].split('Rs.')[1],
                'discount':entry[1].split('Rs.')[2],
                'taxable_amount':entry[1].split('Rs.')[3],
                'cgst':entry[2].split('Rs.')[1].strip(),
            }
            result.append(price)
        total_amount = {
            'tax':raw_total.split('Rs.')[1].strip(),
            'total':raw_total.split('Rs.')[2].strip(),
        }
        result.append(total_amount)
        return result

if __name__ == "__main__":
    pdf_path = "/home/alchemist/Downloads/meesho_label.pdf"
    if BasePDFProcessor(pdf_path).get_label_shipper() == "shadowfax":
        shadowfax_pdf_processor = ShadowfaxPDFProcessor(pdf_path)
        print(json.dumps(shadowfax_pdf_processor.result, indent=4))
    else:
        print("Invalid label shipper")