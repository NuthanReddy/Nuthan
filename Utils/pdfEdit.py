import pprint

from PyPDF2 import PdfFileReader, PdfFileWriter

file_in = open('/Users/nuthan/Downloads/Bhavana_Pajjuri_Offer.pdf', 'rb')
pdf_reader = PdfFileReader(file_in)
metadata = pdf_reader.getDocumentInfo()
pprint.pprint(metadata)

pdf_writer = PdfFileWriter()
pdf_writer.appendPagesFromReader(pdf_reader)
pdf_writer.addMetadata({
'/Creator': "Microsoft® Word 2016",
'/Resolution': "612×792",
'/Security': "None",
'/Producer': "",
'/Author': "Brigath Clara"
})
file_out = open('/Users/nuthan/Downloads/BhavanaPajjuri_Offer.pdf', 'wb')
pdf_writer.write(file_out)

file_in.close()
file_out.close()
