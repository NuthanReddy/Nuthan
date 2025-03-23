import pprint

from PyPDF2 import PdfFileReader, PdfFileWriter

file_in = open('/Users/nuthan/Documents/Job/Other Offers/Congratulations_on_your_Visa_Offer_Bhavana2.pdf', 'rb')
pdf_reader = PdfFileReader(file_in)
metadata = pdf_reader.getDocumentInfo()
pprint.pprint(metadata)

pdf_writer = PdfFileWriter()
pdf_writer.appendPagesFromReader(pdf_reader)
pdf_writer.addMetadata({
'/Security': "None",
'/Producer': "PDFKit.NET 23.2.1.41453 DMV9",
'/Author': "Talreja Rama - WW970D3102"
})
file_out = open('/Users/nuthan/Documents/Job/Other Offers/Congratulations_on_your_Visa_Offer_Bhavana.pdf', 'wb')
pdf_writer.write(file_out)

file_in.close()
file_out.close()
