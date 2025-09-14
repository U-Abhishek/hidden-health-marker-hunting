import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

class ICalendarParser:
    def __init__(self, ics_file_path: str):
        self.ics_file_path = ics_file_path
        self.calendar_data = {
            "calendar_info": {},
            "events": []
        }
    
    def parse_icalendar(self) -> Dict[str, Any]:
        """Parse the iCalendar file and return structured JSON data"""
        with open(self.ics_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parse calendar properties
        self._parse_calendar_properties(content)
        
        # Parse events
        self._parse_events(content)
        
        return self.calendar_data
    
    def _parse_calendar_properties(self, content: str):
        """Extract calendar-level properties"""
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('PRODID:'):
                self.calendar_data["calendar_info"]["product_id"] = line[7:]
            elif line.startswith('VERSION:'):
                self.calendar_data["calendar_info"]["version"] = line[8:]
            elif line.startswith('CALSCALE:'):
                self.calendar_data["calendar_info"]["calendar_scale"] = line[9:]
            elif line.startswith('METHOD:'):
                self.calendar_data["calendar_info"]["method"] = line[7:]
            elif line.startswith('X-WR-CALNAME:'):
                self.calendar_data["calendar_info"]["calendar_name"] = line[13:]
            elif line.startswith('X-WR-TIMEZONE:'):
                self.calendar_data["calendar_info"]["timezone"] = line[14:]
    
    def _parse_events(self, content: str):
        """Extract all events from the iCalendar content"""
        # Split content into individual events
        event_blocks = re.split(r'BEGIN:VEVENT', content)
        
        for block in event_blocks[1:]:  # Skip first empty block
            event = self._parse_single_event(block)
            if event:
                self.calendar_data["events"].append(event)
    
    def _parse_single_event(self, event_block: str) -> Optional[Dict[str, Any]]:
        """Parse a single event block"""
        event = {
            "uid": "",
            "summary": "",
            "description": "",
            "location": "",
            "start_time": "",
            "end_time": "",
            "organizer": "",
            "attendees": [],
            "status": "",
            "created": "",
            "last_modified": "",
            "recurrence": "",
            "alarms": []
        }
        
        lines = event_block.split('\n')
        current_line = ""
        
        for line in lines:
            line = line.strip()
            
            # Handle line continuation (lines starting with space or tab)
            if line.startswith(' ') or line.startswith('\t'):
                current_line += line[1:]
                continue
            else:
                if current_line:
                    self._process_event_line(current_line, event)
                current_line = line
            
            # Stop at END:VEVENT
            if line == 'END:VEVENT':
                break
        
        # Process the last line if it exists
        if current_line and current_line != 'END:VEVENT':
            self._process_event_line(current_line, event)
        
        return event if event["uid"] else None
    
    def _process_event_line(self, line: str, event: Dict[str, Any]):
        """Process a single line of event data"""
        if line.startswith('UID:'):
            event["uid"] = line[4:]
        elif line.startswith('SUMMARY:'):
            event["summary"] = line[8:]
        elif line.startswith('DESCRIPTION:'):
            event["description"] = line[12:]
        elif line.startswith('LOCATION:'):
            event["location"] = line[9:]
        elif line.startswith('DTSTART'):
            event["start_time"] = self._parse_datetime(line)
        elif line.startswith('DTEND'):
            event["end_time"] = self._parse_datetime(line)
        elif line.startswith('ORGANIZER'):
            event["organizer"] = self._parse_organizer(line)
        elif line.startswith('ATTENDEE'):
            attendee = self._parse_attendee(line)
            if attendee:
                event["attendees"].append(attendee)
        elif line.startswith('STATUS:'):
            event["status"] = line[7:]
        elif line.startswith('CREATED:'):
            event["created"] = self._parse_datetime(line)
        elif line.startswith('LAST-MODIFIED:'):
            event["last_modified"] = self._parse_datetime(line)
        elif line.startswith('RRULE:'):
            event["recurrence"] = line[6:]
        elif line.startswith('BEGIN:VALARM'):
            # Handle alarms (simplified)
            event["alarms"].append("Alarm present")
    
    def _parse_datetime(self, line: str) -> str:
        """Parse datetime from iCalendar format"""
        # Extract datetime part after colon
        dt_part = line.split(':', 1)[1] if ':' in line else ""
        
        # Handle different datetime formats
        if 'T' in dt_part and 'Z' in dt_part:
            # UTC datetime format: 20200528T043000Z
            try:
                dt = datetime.strptime(dt_part, '%Y%m%dT%H%M%SZ')
                return dt.isoformat() + 'Z'
            except ValueError:
                return dt_part
        elif 'T' in dt_part:
            # Local datetime format: 20200528T043000
            try:
                dt = datetime.strptime(dt_part, '%Y%m%dT%H%M%S')
                return dt.isoformat()
            except ValueError:
                return dt_part
        else:
            return dt_part
    
    def _parse_organizer(self, line: str) -> str:
        """Parse organizer information"""
        # Extract email from organizer line
        if 'mailto:' in line:
            email_match = re.search(r'mailto:([^;]+)', line)
            if email_match:
                return email_match.group(1)
        
        # Extract CN (Common Name) if available
        cn_match = re.search(r'CN=([^;:]+)', line)
        if cn_match:
            return cn_match.group(1)
        
        return line.split(':', 1)[1] if ':' in line else ""
    
    def _parse_attendee(self, line: str) -> Optional[Dict[str, str]]:
        """Parse attendee information"""
        attendee = {}
        
        # Extract email
        email_match = re.search(r'mailto:([^;]+)', line)
        if email_match:
            attendee["email"] = email_match.group(1)
        
        # Extract CN (Common Name)
        cn_match = re.search(r'CN=([^;:]+)', line)
        if cn_match:
            attendee["name"] = cn_match.group(1)
        
        # Extract participation status
        status_match = re.search(r'PARTSTAT=([^;]+)', line)
        if status_match:
            attendee["status"] = status_match.group(1)
        
        # Extract role
        role_match = re.search(r'ROLE=([^;]+)', line)
        if role_match:
            attendee["role"] = role_match.group(1)
        
        return attendee if attendee else None
    
    def save_to_json(self, output_file: str):
        """Save the parsed calendar data to a JSON file"""
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(self.calendar_data, file, indent=2, ensure_ascii=False)

    # return the calendar data object
    def get_calendar_data(self):
        return self.calendar_data

def extract_calendar_data(ics_file: str, output_file: str):
    """Main function to extract iCalendar data to JSON"""
    
    if not os.path.exists(ics_file):
        print(f"Error: iCalendar file not found at {ics_file}")
        return None
    
    print(f"Parsing iCalendar file: {ics_file}")
    parser = ICalendarParser(ics_file)
    
    try:
        calendar_data = parser.parse_icalendar()
        
        # Save to JSON
        parser.save_to_json(output_file)
        
        print(f"Successfully extracted calendar data to: {output_file}")
        print(f"Calendar: {calendar_data['calendar_info'].get('calendar_name', 'Unknown')}")
        print(f"Total events: {len(calendar_data['events'])}")
        
        # Show sample event
        if calendar_data['events']:
            sample_event = calendar_data['events'][0]
            print(f"\nSample event:")
            print(f"  Summary: {sample_event.get('summary', 'N/A')}")
            print(f"  Start: {sample_event.get('start_time', 'N/A')}")
            print(f"  Location: {sample_event.get('location', 'N/A')}")
            print(f"  Attendees: {len(sample_event.get('attendees', []))}")
        
        # Return the calendar data so it can be used for operations
        return calendar_data
        
    except Exception as e:
        print(f"Error parsing iCalendar file: {str(e)}")
        return None


def oprate_calendar_data(ics_file: str):
    """Main function to operate on calendar data"""
    
    if not os.path.exists(ics_file):
        print(f"Error: iCalendar file not found at {ics_file}")
        return
    
    print(f"Parsing iCalendar file: {ics_file}")
    parser = ICalendarParser(ics_file)
    
    try:
        # Parse the calendar data
        calendar_data = parser.parse_icalendar()


        # extract events from the calendar data

        # output format i need


        
        return  calendar_data
        
    except Exception as e:
        print(f"Error processing calendar data: {str(e)}")


if __name__ == "__main__":
    oprate_calendar_data(ics_file = "../data/calender_data_2.ics")
