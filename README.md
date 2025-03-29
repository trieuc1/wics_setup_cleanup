# Setup/Cleanup Shift Assigner
This project is used for WICS @ UCI to help assign setup and cleanup shifts to committee based on various requirements.
- It will create a quarter_schedule.txt outlining everyone's shifts for the quarter so that it is easy to copy to the setup/cleanup general spreadsheet
- It will create a week_schedule.txt outlining everyone's shifts week by week with labels of who is a leader and a shadow, making it easy to copy to the weeks sections of the setup/cleanup spreadsheet

## Required Files
**In project folder**
- preference.txt
  contains the shifts preferences with columns of their first name, last name, their shift preferences, leader, [optional] shadow 
  - [preferences [regular].txt](https://github.com/user-attachments/files/19522126/preferences.txt)
  - [preferences [shadow].txt](https://github.com/user-attachments/files/19522145/preferences.txt)

## Instructions
### constants.py
Adjust these constants to fit your criteria. If the code fails to assign shifts, adjust these constants until the code successfully completes.
  
- MIN_SETUP - minimum of people that should be on a setup shift
- MIN_CLEANUP - minimum of people that should be on a cleanup shift
- MAX_SHIFTS - maximum number of shifts that a person should have
- MIN_SHIFTS - minimum number of shifts that a person should have
- MAX_CONSECUTIVE_SHIFTS - maximum number of consecutive shifts that a person should have
- MODE - can be "shadowing" or "regular"

### assign_shifts.py
In the run function, adjust the **weeks** variable to have a list of weeks that you want to assign shifts to.
Run the assign_shifts.py file to create shift assignments.
