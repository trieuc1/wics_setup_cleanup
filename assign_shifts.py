import random
from constants import (MIN_CLEANUP, MIN_SETUP, MIN_SHIFTS, MAX_CONSECUTIVE_SHIFTS, 
                       MAX_SHIFTS, NUM_CLEANUP_LEADERS, NUM_SETUP_LEADERS, NUM_SETUP_SHADOWS, NUM_CLEANUP_SHADOWS, MODE)


def parse_file(file : str) -> dict:
    with open(file, 'r') as file:
        preference_dict = {}
        for line in file:
            parts = line.split()
            name = []
            shift_preference = ""
            if MODE == "shadowing":
                is_leader = parts[-2] == '1'
                is_shadow = parts[-1] == '1'
            else:
                is_leader = parts[-1] == '1'
            skip_flag = False
            for part in parts:
                if part not in ['s', 'c', 's/c', '-'] and not part.isdigit():
                    name.append(part)
                elif part in ['s', 'c', 's/c', '-']:
                    if part == "-":
                        skip_flag = True
                    shift_preference = part
            if skip_flag is True:
                continue
            name = " ".join(name)
            if MODE == "shadowing":
                preference_dict[name] = {"preference" : shift_preference, "is_leader": is_leader, "is_shadow": is_shadow}
            else:
                preference_dict[name] = {"preference" : shift_preference, "is_leader": is_leader}
        return preference_dict
    return None


def track_person_shifts(assignment_dict: dict):
    """
    Helper function to track total shifts, consecutive shifts, and consecutive leadership shifts for each person.

    :param assignment_dict: Dictionary containing weekly shift assignments.
    :return: person_shift_count, person_shift_sequence, leader_shift_sequence
    """
    person_shift_count = {}  # Tracks total shifts per person
    person_shift_sequence = {}  # Tracks consecutive shifts per person
    leader_shift_sequence = {}  # Tracks consecutive leadership shifts per person
    shadow_shift_sequence = {}

    for week_index, (week, shifts) in enumerate(assignment_dict.items()):
        # Validate setup group
        setup_group = shifts.get("setup", [])
        # Validate cleanup group
        cleanup_group = shifts.get("cleanup", [])

        # Update shift and leadership tracking
        for group, role in [(setup_group, "setup"), (cleanup_group, "cleanup")]:
            for person in group:
                name = person["name"]
                is_leader = person["leader_this_week"]
                is_shadow = person["shadow_this_week"]
                

                # Track total shift count
                person_shift_count[name] = person_shift_count.get(name, 0) + 1

                # Track consecutive shifts
                if name not in person_shift_sequence:
                    person_shift_sequence[name] = []
                if len(person_shift_sequence[name]) > 0 and person_shift_sequence[name][-1] != week_index - 1:
                    person_shift_sequence[name] = []  # Reset if not consecutive
                person_shift_sequence[name].append(week_index)

                # Track consecutive leadership shifts
                if is_leader:
                    if name not in leader_shift_sequence:
                        leader_shift_sequence[name] = []
                    if len(leader_shift_sequence[name]) > 0 and leader_shift_sequence[name][-1] != week_index - 1:
                        leader_shift_sequence[name] = []  # Reset if not consecutive
                    leader_shift_sequence[name].append(week_index)
                
                if is_shadow:
                    if name not in shadow_shift_sequence:
                        shadow_shift_sequence[name] = []
                    if len(shadow_shift_sequence[name]) > 0 and shadow_shift_sequence[name][-1] != week_index - 1:
                        shadow_shift_sequence[name] = []  # Reset if not consecutive
                    shadow_shift_sequence[name].append(week_index)

    return person_shift_count, person_shift_sequence, leader_shift_sequence, shadow_shift_sequence



def is_valid_assignment(assignment_dict: dict) -> bool:
    """
    Returns whether an assignment is valid or not.

    Criteria:
    - Each person has fewer than MAX_SHIFTS shifts.
    - Can't have more than MAX_CONSECUTIVE_SHIFTS shifts in a row.
    - Each week has:
        - At least MIN_SETUP people in the setup group (NUM_SETUP_LEADERS leaders).
        - At least MIN_CLEANUP people in the cleanup group (NUM_CLEANUP_LEADERS leader).
    """
    person_shift_count, person_shift_sequence, leader_shift_sequence, shadow_shift_sequence = track_person_shifts(assignment_dict)
    
    for shifts in assignment_dict.values():
        if len(shifts["setup"]) < MIN_SETUP or sum(p["leader_this_week"] for p in shifts["setup"]) < NUM_SETUP_LEADERS:
            print("ERROR: required number of setup or setup leaders is not met")
            return False
        if len(shifts["cleanup"]) < MIN_CLEANUP or sum(p["leader_this_week"] for p in shifts["cleanup"]) < NUM_CLEANUP_LEADERS:
            print("ERROR: required number of cleanup or cleanup leaders is not met")
            return False
        
        if MODE == "shadowing":
            # Ensure at least one leader and one shadow in both setup and cleanup
            if not any(p["leader_this_week"] for p in shifts["setup"]) or not any(p["shadow_this_week"] for p in shifts["setup"]):
                print("ERROR: required number of setup shadows or setup leaders is not met")
                return False  # Setup lacks a leader or shadow

            if not any(p["leader_this_week"] for p in shifts["cleanup"]) or not any(p["shadow_this_week"] for p in shifts["cleanup"]):
                print("ERROR: required number of cleanup shadows or cleanup leaders is not met")
                return False  # Cleanup lacks a leader or shadow

    if not all(len(seq) <= MAX_CONSECUTIVE_SHIFTS for seq in leader_shift_sequence.values()):
            print("ERROR: maximum number of consecutive shifts for leaders exceeded")
            return False
    
    if not all(len(seq) <= MAX_CONSECUTIVE_SHIFTS for seq in person_shift_sequence.values()):
            print("ERROR: maximum number of consecutive shifts for people exceeded")
            return False
    
    if not all(len(seq) <= MAX_CONSECUTIVE_SHIFTS for seq in shadow_shift_sequence.values()):
        print("ERROR: maximum number of consecutive shifts for shadows exceeded")
        return False
    
    # Validate total shifts
    if not all(MIN_SHIFTS <= count <= MAX_SHIFTS for name, count in person_shift_count.items() if count for seq in [person_shift_sequence.get(name, [])]):
        print("ERROR: somebody has too little or too many shifts")
        return False
    
    return True
    

def assign_shifts_backtracker(preference_dict: dict, weeks: list) -> dict:
    """
    Main function to assign shifts using backtracking with constraints.
    Ensures 2 leaders for setup and 1 leader for cleanup per week,
    avoiding three consecutive weeks of leadership for participants.

    :param preference_dict: Dictionary containing people's preferences and leader status.
    :param weeks: List of weeks (e.g., ["Week 1", "Week 2", ...]).
    :return: Dictionary of valid shift assignments or None if no valid assignment exists.
    """

    assignment_dict = {week: {"setup": [], "cleanup": []} for week in weeks}
    leader_last_week = {person: [] for person in preference_dict}  # Track all weeks where a person was a leader
    shadow_last_week = {person: [] for person in preference_dict}  # Track all weeks where a person was a shadow

    def backtracking_helper(index: int) -> bool:
        """
        Recursive helper for backtracking with constraints:
        - Ensure 2 leaders for setup and 1 leader for cleanup.
        - Prevent participants from being leaders for three consecutive weeks.
        - Fill each week completely (7 setup, 5 cleanup) before moving to the next.

        :param index: Current week index.
        :return: True if a valid assignment is found, False otherwise.
        """
        if index == len(weeks):
            # return is_valid_assignment(assignment_dict)
            return True

        current_week = weeks[index]

        # Sort participants randomly (shuffling before sorting)
        randomized_items = list(preference_dict.items())  # Convert items to a list
        random.shuffle(randomized_items)  # Shuffle the list in place

        leaders = [person for person in randomized_items if person[1]["is_leader"]]
        shadows = [person for person in randomized_items if person[1].get("is_shadow", False) and not person[1]["is_leader"]]

        # Sort the leaders based on the number of shifts they've had
        leaders_sorted = sorted(leaders, key=lambda x: len([
            shift for week in assignment_dict.values()
            for shift in (week["setup"] + week["cleanup"]) if shift["name"] == x[0]
        ]))

        remaining_setup_leaders = NUM_SETUP_LEADERS
        remaining_cleanup_leaders = NUM_CLEANUP_LEADERS

        # Step 1: First, try to assign leaders to setup and cleanup
        for person, preferences in leaders_sorted:
            person_shift_count, person_shift_sequence, leader_shift_sequence, shadow_shift_sequence = track_person_shifts(assignment_dict)

            # Prevent double assignment in the same week (setup + cleanup)
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue
            
            # Ensure nobody that already has MAX_SHIFTS is assigned another shifts
            if person_shift_count.get(person, 0) >= MAX_SHIFTS:
                continue
            
            # Ensure that person that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(person_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and person_shift_sequence[person][-1] == (index - 1):
                continue
            
            # Ensure that leader that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(leader_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and leader_shift_sequence[person][-1] == (index - 1):
                continue
        
            # Ensure that shadow that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(shadow_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and shadow_shift_sequence[person][-1] == (index - 1):
                continue

            # Assign to setup first (leaders only)
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP and \
                preferences["is_leader"] and remaining_setup_leaders > 0:
                    leader_this_week = True
                    assignment_dict[current_week]["setup"].append({
                        "name": person,
                        "is_leader": preferences["is_leader"],
                        "is_shadow": preferences.get("is_shadow", False),
                        "shadow_this_week": False,
                        "leader_this_week": leader_this_week
                    })
                    leader_last_week[person].append(index)
                    remaining_setup_leaders -= 1
                    continue
            # Assign to cleanup (leaders only)
            elif preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP and \
                preferences["is_leader"] and remaining_cleanup_leaders > 0:
                    leader_this_week = True
                    assignment_dict[current_week]["cleanup"].append({
                        "name": person,
                        "is_leader": preferences["is_leader"],
                        "is_shadow": preferences.get("is_shadow", False),
                        "shadow_this_week": False,
                        "leader_this_week": leader_this_week
                    })
                    leader_last_week[person].append(index)
                    remaining_cleanup_leaders -= 1
                    continue

            # If we've successfully assigned leaders for setup and cleanup, move on to the next week
            if (len(assignment_dict[current_week]["setup"]) == MIN_SETUP and
                len(assignment_dict[current_week]["cleanup"]) == MIN_CLEANUP):
                if backtracking_helper(index + 1):
                    return True

                # If we can't assign, backtrack and remove the assignments
                if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) > 0:
                    assignment_dict[current_week]["setup"].pop()
                    if leader_this_week and leader_last_week[person]:
                        leader_last_week[person].pop()

                if preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) > 0:
                    assignment_dict[current_week]["cleanup"].pop()
                    if leader_this_week and leader_last_week[person]:
                        leader_last_week[person].pop()

        # Step 1a: Try to assign shadow leaders to setup and cleanup
        shadows_sorted = sorted(shadows, key=lambda x: len([
            shift for week in assignment_dict.values()
            for shift in (week["setup"] + week["cleanup"]) if shift["name"] == x[0]
        ]))
        
        remaining_setup_shadows = NUM_SETUP_SHADOWS
        remaining_cleanup_shadows = NUM_CLEANUP_SHADOWS
        
        for person, preferences in shadows_sorted:
            if remaining_setup_shadows == 0 and remaining_cleanup_shadows == 0:
                break
            
            person_shift_count, person_shift_sequence, leader_shift_sequence, shadow_shift_sequence = track_person_shifts(assignment_dict)
            
            # Prevent double assignment in the same week (setup + cleanup)
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue
            
            # Ensure nobody that already has MAX_SHIFTS is assigned another shifts
            if person_shift_count.get(person, 0) >= MAX_SHIFTS:
                continue
            
            # Ensure that person that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(person_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and person_shift_sequence[person][-1] == (index - 1):
                continue
            
            # Ensure that leader that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(leader_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and leader_shift_sequence[person][-1] == (index - 1):
                continue
                
            # Ensure that shadow that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(shadow_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and shadow_shift_sequence[person][-1] == (index - 1):
                continue
            
            shadow_this_week = False
            
            # Assign to setup first (shadows only)
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP and \
                preferences["is_shadow"] and remaining_setup_shadows > 0:
                    shadow_this_week = True
                    assignment_dict[current_week]["setup"].append({
                        "name": person,
                        "is_leader": False,
                        "is_shadow": preferences["is_shadow"],
                        "shadow_this_week": shadow_this_week,
                        "leader_this_week": False,
                    })
                    shadow_last_week[person].append(index)
                    remaining_setup_shadows -= 1
                    continue
            # Assign to cleanup (shadows only)
            elif preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP and \
                preferences["is_shadow"] and remaining_cleanup_shadows > 0:
                    shadow_this_week = True
                    assignment_dict[current_week]["cleanup"].append({
                        "name": person,
                        "is_leader": False,
                        "is_shadow": preferences["is_shadow"],
                        "shadow_this_week": shadow_this_week,
                        "leader_this_week": False
                    })
                    shadow_last_week[person].append(index)
                    remaining_cleanup_shadows -= 1
                    continue

            # If we've successfully assigned leaders for setup and cleanup, move on to the next week
            if (len(assignment_dict[current_week]["setup"]) == MIN_SETUP and
                len(assignment_dict[current_week]["cleanup"]) == MIN_CLEANUP):
                if backtracking_helper(index + 1):
                    return True

                # If we can't assign, backtrack and remove the assignments
                if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) > 0:
                    assignment_dict[current_week]["setup"].pop()
                    if shadow_this_week and shadow_last_week[person]:
                        shadow_last_week[person].pop()

                if preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) > 0:
                    assignment_dict[current_week]["cleanup"].pop()
                    if shadow_this_week and shadow_last_week[person]:
                        shadow_last_week[person].pop()
                        
        # Step 2: Once leaders are assigned, fill the remaining spots with non-leaders
        
        # Sort participants by the number of shifts they've already been assigned to
        participants = sorted(randomized_items, key=lambda x: len([
            shift for week in assignment_dict.values()
            for shift in (week["setup"] + week["cleanup"]) if shift["name"] == x[0]
        ]))
        
        for person, preferences in participants:
            person_shift_count, person_shift_sequence, leader_shift_sequence, shadow_shift_sequence = track_person_shifts(assignment_dict)
            
            # Prevent double assignment in the same week (setup + cleanup)
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue
            
            # Ensure nobody that already has MAX_SHIFTS is assigned another shifts
            if person_shift_count.get(person, 0) >= MAX_SHIFTS:
                continue
            
            # Ensure that person that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(person_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and person_shift_sequence[person][-1] == (index - 1):
                continue
            
            # Ensure that leader that already has MAX_CONSECUTIVE_SHIFTS receives another consecutive shift
            if len(leader_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and leader_shift_sequence[person][-1] == (index - 1):
                continue
                
            if len(shadow_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and shadow_shift_sequence[person][-1] == (index - 1):
                    continue

            # Assign to setup for non-leaders
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP:
                assignment_dict[current_week]["setup"].append({
                    "name": person,
                    "is_leader": preferences["is_leader"],
                    "is_shadow": preferences.get("is_shadow", False),
                    "leader_this_week": False,
                    "shadow_this_week": False
                })

            # Assign to cleanup for non-leaders
            elif preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP:
                assignment_dict[current_week]["cleanup"].append({
                    "name": person,
                    "is_leader": preferences["is_leader"],
                    "is_shadow": preferences.get("is_shadow", False),
                    "leader_this_week": False,
                    "shadow_this_week": False
                })

            # If we've filled both setup and cleanup, move on to the next week
            if (len(assignment_dict[current_week]["setup"]) == MIN_SETUP and
                len(assignment_dict[current_week]["cleanup"]) == MIN_CLEANUP):
                if backtracking_helper(index + 1):
                    return True

                # Backtrack if assignment fails
                if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) > 0:
                    assignment_dict[current_week]["setup"].pop()

                if preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) > 0:
                    assignment_dict[current_week]["cleanup"].pop()

        return False  # If no valid assignment found, backtrack

    # Start backtracking from week 0
    if backtracking_helper(0):
        print("Is it true that the following assignments are valid?", is_valid_assignment(assignment_dict))
        return assignment_dict  # Return the successfully filled assignment
    
    return None  # Return None if no valid assignment could be found


def save_assignments_to_week_file(assignments_by_week: dict, output_file: str) -> None:
    """
    Save the shift assignments for multiple weeks to a single text file, with space between weeks.

    :param assignments_by_week: Dictionary where keys are week names (e.g., "Week 1") and values are assignment_dicts.
    :param output_file: Path to the output text file.
    """
    with open(output_file, 'w') as file:
        for week, shifts in assignments_by_week.items():
            file.write(f"Shift Assignments for {week}:\n")
            file.write("=" * 50 + "\n\n")

            file.write("  Setup:\n")
            for person in shifts["setup"]:
                if person['leader_this_week']:
                    file.write(f"     {person['name']} (Leader)\n")
                elif person['shadow_this_week'] and MODE == "shadowing":
                    file.write(f"     {person['name']} (Shadow)\n")
                else:
                    file.write(f"     {person['name']}\n")

            file.write("\n  Cleanup:\n")
            for person in shifts["cleanup"]:
                if person['leader_this_week']:
                    file.write(f"     {person['name']} (Leader)\n")
                elif person['shadow_this_week'] and MODE == "shadowing":
                    file.write(f"     {person['name']} (Shadow)\n")
                else:
                    file.write(f"     {person['name']}\n")

            file.write("\n\n" + "-" * 50 + "\n\n")

    print(f"Assignments saved to {output_file}")


def save_assignments_to_quarter_file(preference_dict: dict, assignments_by_week: dict,  weeks: list, output_file: str) -> None:
    """
    Save the shift assignments for multiple weeks to a single text file, with space between weeks.
    
    :param preference_dict: Dictionary with name, shift preference, and leadership status.
    :param assignments_by_week: Dictionary where keys are week names (e.g., "Week 1") and values are assignment_dicts.
    :param weeks: List of weeks to include in the output (e.g., ["Week 1", "Week 2", "Week 4", ...]).
    :param output_file: Path to the output text file.
    """
    # Prepare a dictionary to store the final assignments for each person across all weeks
    person_assignments = {person: {'setup': 0, 'cleanup': 0, 'leader': 0, 'weeks': {week: '' for week in weeks}} for person in preference_dict}

    # Process the assignments from each week and fill the person's assignments
    for week in assignments_by_week:
        if week not in weeks:
            continue  # Skip weeks not in the provided list

        for shift_type in ["setup", "cleanup"]:
            for person in assignments_by_week[week][shift_type]:
                # Check if the person exists in the preference_dict and assign them to the week
                if person['name'] in preference_dict:
                    # Get preference status from preference_dict
                    preference = preference_dict[person['name']]['preference']

                    # Track the setup and cleanup assignments
                    person_assignments[person['name']]['setup'] += 1 if shift_type == 'setup' else 0
                    person_assignments[person['name']]['cleanup'] += 1 if shift_type == 'cleanup' else 0
                    

                    # Update the person's assignment for the week
                    person_assignments[person['name']]['weeks'][week] = 's' if shift_type == "setup" else 'c'

    # Write to the output file
    with open(output_file, 'w') as file:
        # Write the header row
        all_weeks = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7", "Week 8", "Week 9", "Week 10"]
        if MODE == "shadowing":
            file.write("First Name\tLast Name\tPreference\tLeader\tShadow\tTotals\t" + "\t".join(all_weeks) + "\n")
        else:
            file.write("First Name\tLast Name\tPreference\tLeader\tTotals\t" + "\t".join(all_weeks) + "\n")
        
        # Write each person's row of assignments
        for person, assignments in person_assignments.items():
            name_parts = person.split()
            first_name = name_parts[0]
            last_name = name_parts[-1]
            preference = preference_dict[person]['preference']
            leader_status = int(preference_dict[person]['is_leader'])
            total_shifts = assignments['setup'] + assignments['cleanup']
            
            if MODE == "shadowing":
                shadow_status = int(preference_dict[person]['is_shadow'])
                # Prepare the row with the person's data
                row = [first_name, last_name, preference, leader_status, shadow_status, total_shifts]
            else:
                row = [first_name, last_name, preference, leader_status, total_shifts]

            # Add the week-specific assignments to the row
            for week in all_weeks:
                if week in weeks:
                    row.append(assignments['weeks'][week])
                else:
                    row.append("")

            # Write the row to the file
            file.write("\t".join(map(str, row)) + "\n")

    print(f"Assignments saved to {output_file}")


def run():
    file_name = "preferences.txt"
    weeks = ["Week 1", "Week 2", "Week 4", "Week 5", "Week 6", "Week 8", "Week 9", "Week 10"]
    preference_dict = parse_file(file_name)
    if sum(1 for v in preference_dict.values() if v["is_leader"]) < len(weeks):
        raise ValueError("Not enough leaders to assign at least one per week.")
    assignment_dict = assign_shifts_backtracker(preference_dict, weeks)
    while assignment_dict is None:
        assignment_dict = assign_shifts_backtracker(preference_dict, weeks)
    if assignment_dict:
        save_assignments_to_week_file(assignment_dict, "week_schedule.txt")
        save_assignments_to_quarter_file(preference_dict, assignment_dict, weeks, "quarter_schedule.txt")
    else:
        print("No valid assignment found.")


if __name__ == "__main__":
    run()