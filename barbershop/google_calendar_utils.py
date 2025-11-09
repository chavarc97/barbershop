from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime
from datetime import timedelta

def create_google_calendar_event(access_token, appointment):
    """
    Create a Google Calendar event using the user's access_token (barber or admin)
    """
    creds = Credentials(token=access_token)
    service = build('calendar', 'v3', credentials=creds)

    event_body = {
        'summary': f'Cita con {appointment.client.username}',
        'description': f'Servicio: {appointment.service.name}\nNotas: {appointment.notes}',
        'start': {
            'dateTime': appointment.appointment_datetime.isoformat(),
            'timeZone': 'America/Mexico_City'
        },
        'end': {
            'dateTime': (appointment.appointment_datetime + timedelta(minutes=appointment.duration_minutes)).isoformat(),
            'timeZone': 'America/Mexico_City'
        }
    }

    event = service.events().insert(calendarId='primary', body=event_body).execute()
    return event['id']
