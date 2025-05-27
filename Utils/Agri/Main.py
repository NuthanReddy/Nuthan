from Utils import print_district_list, get_mandals_from_district, get_villages_from_mandal

cookie = "org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en; setAuth=7d8aec23-f622-4814-995f-0573ac5e73f8; JSESSIONID=SRL5v9YJf-7fOD_N6Z1bRnS2XQhbsMQn4SsDHz2W.dharani-app-prod02",

print_district_list()
district_id = input("\nEnter the District ID: ")
district_id = district_id if district_id else 29

get_mandals_from_district(district_id, cookie)
mandal_id = input("\nEnter the Mandal ID: ")
mandal_id = mandal_id if mandal_id else 574

get_villages_from_mandal(mandal_id, cookie)
village_id = input("\nEnter the Village ID: ")
village_id = village_id if village_id else 2917004


