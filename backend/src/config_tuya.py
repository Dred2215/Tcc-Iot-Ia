from tuya_connector import TuyaOpenAPI

ACCESS_ID = "4jgyc5ex3wagcdt5eycs"
ACCESS_SECRET = "fc51f69c94704a548ebb5537809ea9a0"
ENDPOINT = "https://openapi.tuyaus.com"

# >>> Preencha com o UID mostrado no console (home_id)
UID = "az1636816675981dWC2h"
home_id = "54688414"


openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()
