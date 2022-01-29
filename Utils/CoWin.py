import requests
from datetime import datetime, timedelta
import os
import time

district_ids = ["581", "603"] # , "596", "611"
# hyderabad "581"
# rangareddy "603"
# medchal "596"
# yadadri "611"
# sangareddy "604"
# suryapet "606"
# nalgonda "598"
host = "https://cdn-api.co-vin.in/"
api = "api/v2/appointment/sessions/public/findByDistrict"
dose_num = "1"
min_age = 45
# 18
vaccine = "COVISHIELD"
# "COVAXIN"

while True:
    for district_id in district_ids:
        current_date = datetime.today()
        today = current_date.strftime("%d-%m-%Y")
        tomorrow = (current_date + timedelta(days=1)).strftime("%d-%m-%Y")
        day_after_tomorrow = (current_date + timedelta(days=2)).strftime("%d-%m-%Y")
        dates = [tomorrow, day_after_tomorrow] #today,
        for date in dates:
            params = "?district_id={}&date={}".format(district_id, date)
            url = host + api + params
            # print(url)

            sessions_json = requests.get(url).json()
            sessions = sessions_json["sessions"]
            available = [x for x in sessions
                         if x['available_capacity_dose'+dose_num] > 0
                         and x['min_age_limit'] == min_age
                         and x['vaccine'] == vaccine
                         ]
            availability_details = [(x['name'], x['district_name'], x['block_name'], x['vaccine'], x['available_capacity_dose'+dose_num], x['pincode'], x['date'], x['slots']) for x in available]

            if len(availability_details) > 0:
                for a in availability_details:
                    print(a)
                #os.system("open \"https://selfregistration.cowin.gov.in/\"")
                #os.system("open \"/Users/nuthan/Music/Music/Media/Music/Akon/Smack That/02 Smack That.mp3\"")
            time.sleep(3)
    print("done")
    time.sleep(30)





