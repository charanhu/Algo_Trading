# GeneareteToken.py

# Import the required module from the fyers_apiv3 package
from fyers_apiv3 import fyersModel

# Define your Fyers API credentials
client_id = "SPXXXXE7-100"  # Replace with your client ID
secret_key = "N********B"  # Replace with your secret key
redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"  # Replace with your redirect URI
response_type = "code" 
grant_type = "authorization_code"  

# The authorization code received from Fyers after the user grants access
auth_code = "eyJ0eXAi*******.eyJpc3MiOiJhcGkubG9********.r_65Awa1kGdsNTAgD******"

# Create a session object to handle the Fyers API authentication and token generation
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key, 
    redirect_uri=redirect_uri, 
    response_type=response_type, 
    grant_type=grant_type
)

# Set the authorization code in the session object
session.set_token(auth_code)

# Generate the access token using the authorization code
response = session.generate_token()

# Print the response, which should contain the access token and other details
print(response)


# ----------------------------------------------------------------------------------
# Sample Success Response               
# ----------------------------------------------------------------------------------          

# {
#   's': 'ok',
#   'code': 200,
#   'message': '',
#   'access_token': 'eyJ0eXAiOi***.eyJpc3MiOiJh***.HrSubihiFKXOpUOj_7***',
#   'refresh_token': 'eyJ0eXAiO***.eyJpc3MiOiJh***.67mXADDLrrleuEH_EE***'
# }
