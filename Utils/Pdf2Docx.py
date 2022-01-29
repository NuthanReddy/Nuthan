from pdf2docx import Converter

pdf_file = '/Users/nuthan/Documents/Cash Flow/Reamb/Internet/airtel_broadband.pdf'
docx_file = '/Users/nuthan/Documents/Cash Flow/Reamb/Internet/airtel_broadband.docx'

# convert pdf to docx
cv = Converter(pdf_file)
cv.convert(docx_file)      # all pages by default
cv.close()
