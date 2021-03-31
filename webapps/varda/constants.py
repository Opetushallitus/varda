from rest_framework import status

JARJESTAMISMUODOT_KUNTA = ['jm01']
JARJESTAMISMUODOT_YKSITYINEN = ['jm04', 'jm05']
JARJESTAMISMUODOT_PAOS = ['jm02', 'jm03']

SUCCESSFUL_STATUS_CODE_LIST = [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT]

OPINTOPOLKU_HEADERS = {'Caller-Id': 'csc.varda', 'CSRF': 'csc.varda', 'Cookie': 'CSRF=csc.varda'}
