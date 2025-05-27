import requests
import re, time
from bs4 import BeautifulSoup


villId = 2917003
flag = "khatanos"
surveyNoRegex = r".*"


# Open the file in read mode
with open("/Users/nuthan/PycharmProjects/Nuthan/Utils/Agri/Somavaram_SurveyNo_List.txt", "r") as file:
    # Read all lines and store them in a list
    surveyNoList = [surveyNo.strip() for surveyNo in file.readlines()]

# with open("/Users/nuthan/PycharmProjects/Nuthan/Utils/Agri/Somavaram_SurveyKhataMap_0.tsv", "r") as r:
#     surveyNoSeenList = [surveyNo.strip().split("\t")[0] for surveyNo in r.readlines()]
#
# balSurveyNoList = list(set(surveyNoList) - set(surveyNoSeenList))

balSurveyNoList = surveyNoList

print(balSurveyNoList)

version = str(time.time() * 1000)


with open(f"/Users/nuthan/PycharmProjects/Nuthan/Utils/Agri/Somavaram_SurveyKhataMap_{version}.tsv", "w") as f:
    for surveyNo in balSurveyNoList:
        if not re.match(surveyNoRegex, surveyNo):
            continue
        print(surveyNo)
        # Construct the URL with dynamic parameters
        url = f"https://bhubharati.telangana.gov.in/getKhataNoCitizen?villId={villId}&flag={flag}&surveyNo={surveyNo}"

        # Headers remain the same
        headers = {
            "accept": "/",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            "cookie": "org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en; setAuth=7d8aec23-f622-4814-995f-0573ac5e73f8; JSESSIONID=SRL5v9YJf-7fOD_N6Z1bRnS2XQhbsMQn4SsDHz2W.dharani-app-prod02",
            "Referer": "https://bhubharati.telangana.gov.in/knowLandStatus",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }

        # Send the GET request
        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        options = [option['value'] for option in soup.find_all('option') if option['value'] != "0"]

        f.write("\t".join([str(surveyNo), ",".join(options)]) + "\n")