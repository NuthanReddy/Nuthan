

import requests

url = "https://bhubharati.telangana.gov.in/getVillageFromMandalCitizenPortal?mandalId=574"

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

response = requests.get(url, headers=headers)

print(response.text)  # Prints the response content