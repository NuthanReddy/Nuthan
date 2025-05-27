import requests
from bs4 import BeautifulSoup


def extract_options(html):
    soup = BeautifulSoup(html, 'html.parser')
    return {option['value']: option.text.strip() for option in soup.find_all('option') if option['value'] != "0"}


def print_options(map):
    for k, v in map.items():
        print(k, "\t", v)


def print_district_list():
    district_options = '''
    <select name="districtID" tabindex="1" class="form-control for'm-control-sm my-2" id="districtID" onchange="getMandalCitizen(this.value);">
        <option value="0">Please Select</option>
        <option value="13">Adilabad|ఆదిలాబాద్</option>
        <option value="27">Bhadradri Kothagudem|భద్రాద్రి కొత్తగూడెం</option>
        <option value="35">Hanumakonda|హనుమకొండ</option>
        <option value="18">Jagtial|జగిత్యాల్</option>
        <option value="23">Jangoan|జనగాం</option>
        <option value="24">Jayashankar Bhupalpalli|జయశంకర్ భూపాలపల్లి</option>
        <option value="2">Jogulamba Gadwal|జోగులాంబ గద్వాల</option>
        <option value="12">Kamareddy|కామారెడ్డి</option>
        <option value="17">Karimnagar|కరీంనగర్</option>
        <option value="26">Khammam|ఖమ్మం</option>
        <option value="16">Kumuram Bheem (Asifabad)|కుమురం భీమ్ (ఆసిఫాబాద్)</option>
        <option value="25">Mahabubabad|మహబూబాబాద్</option>
        <option value="1">Mahabubnagar|మహబూబ్ నగర్</option>
        <option value="15">Mancherial|మంచిర్యాల్</option>
        <option value="8">Medak|మెదక్</option>
        <option value="6">Medchal-Malkajigiri|మేడ్చల్-మల్కాజిగిరి</option>
        <option value="33">Mulug|ములుగు</option>
        <option value="3">Nagarkurnool|నాగర్ కర్నూల్</option>
        <option value="28">Nalgonda|నల్గొండ</option>
        <option value="32">Narayanpet|నారయణ పేట్</option>
        <option value="14">Nirmal|నిర్మల్</option>
        <option value="11">Nizamabad|నిజామాబాద్</option>
        <option value="20">Peddapalli|పెద్దపల్లి</option>
        <option value="19">Rajanna Sircilla|రాజన్నసిరిసిల్ల</option>
        <option value="5">Rangareddy|రంగా రెడ్డి</option>
        <option value="9">Sangareddy|సంగారెడ్డి</option>
        <option value="10">Siddipet|సిద్దిపేట్</option>
        <option value="29">Suryapet|సూర్యాపేట</option>
        <option value="7">Vikarabad|వికారాబాద్</option>
        <option value="4">Wanaparthy|వనపర్తి</option>
        <option value="34">Warangal|వరంగల్</option>
        <option value="30">Yadadri Bhuvanagiri|యాదాద్రి భువనగిరి</option>
    </select>
    '''

    district_map = extract_options(district_options)
    print_options(district_map)


def get_mandals_from_district(district_id, cookie):

    url = f"https://bhubharati.telangana.gov.in/getMandalFromDivisionCitizenPortal?district={district_id}"

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
    mandal_options = response.text
    mandal_map = extract_options(mandal_options)
    print_options(mandal_map)


def get_villages_from_mandal(mandal_id, cookie):
    url = f"https://bhubharati.telangana.gov.in/getVillageFromMandalCitizenPortal?mandalId={mandal_id}"

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
    village_options = response.text
    village_map = extract_options(village_options)
    print_options(village_map)