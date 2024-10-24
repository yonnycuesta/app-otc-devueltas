import requests

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Token 092c72cfaf87410971e74c640fbe9d53f8c1eda6",
    "Organization": "164"
    }

mensajes_errores = []


def RunApi(URL):
    api_url = URL
    try:
        response = requests.get(api_url,headers=headers)

        if response.status_code in [200,201]:
            return response.json()
        else:
            data = response.json()
            mensajes_errores.append("Datos de la API: ", data)
            return ("Datos de la API: ", data)
               
    except requests.exceptions.RequestException as e:
        mensajes_errores.append(f"Error al realizar la solicitud a la API: {str(e)}")
        return (f"Error al realizar la solicitud a la API: {str(e)}")
        
    except Exception as e:
        mensajes_errores.append(f"Ocurrió un error: {str(e)}")
        return (f"Ocurrió un error: {str(e)}")


                      
