Invoke-RestMethod -Uri "http://localhost:3000/"

#Root URL path fails since we dont a router handling it
Invoke-RestMethod -Uri "http://localhost:3000/vehicle/get_vehicle" -Method Get

#This a POST handler
Invoke-RestMethod -Uri "http://localhost:3000/vehicle/post_vehicle" -Method Post