import random

MIN_SETUP = 8
MIN_CLEANUP = 6
REQUIRED_SETUP_LEADERS = 2
REQUIRED_CLEANUP_LEADERS = 1
MAX_SHIFTS = 5
MIN_SHIFTS = 2
MAX_CONSECUTIVE_SHIFTS = 2

def parse_file(file : str) -> dict:
    with open(file, 'r') as file:
        preference_dict = {}
        for line in file:
            parts = line.split()
            name = []
            shift_preference = ""
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

    return person_shift_count, person_shift_sequence, leader_shift_sequence


def is_valid_assignment(assignment_dict: dict) -> bool:
    """
    Returns whether an assignment is valid or not.

    Criteria:
    - Each person has fewer than MAX_SHIFTS shifts.
        - Can't have more than 2 shifts in a row.
    - Leaders can't be leaders more than two shifts in a row.
    - Each week has:
        - At least 7 people in the setup group (2 leaders).
        - At least 5 people in the cleanup group (1 leader).
    """
    person_shift_count = {}  # Tracks total shifts per person
    person_shift_sequence = {}  # Tracks consecutive shifts per person
    leader_shift_sequence = {}  # Tracks consecutive leadership shifts per person

    for week_index, (week, shifts) in enumerate(assignment_dict.items()):
        # Validate setup group
        setup_group = shifts.get("setup", [])
        if len(setup_group) < MIN_SETUP:
            print("less than min setup")
            return False
        if sum(1 for person in setup_group if person["leader_this_week"]) < REQUIRED_SETUP_LEADERS:
            print("less than min setup leaders")
            return False

        # Validate cleanup group
        cleanup_group = shifts.get("cleanup", [])
        if len(cleanup_group) < MIN_CLEANUP:
            print("less than min cleanup")
            return False
        if sum(1 for person in cleanup_group if person["leader_this_week"]) < REQUIRED_CLEANUP_LEADERS:
            print("less than min cleanup leaders")
            return False

        # Update shift and leadership tracking
        for group, role in [(setup_group, "setup"), (cleanup_group, "cleanup")]:
            for person in group:
                name = person["name"]
                is_leader = person["leader_this_week"]

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

    # Validate total shift count per person
    if any(count > MAX_SHIFTS for count in person_shift_count.values()):
        print("more than max shifts", person_shift_count)
        return False
    
    # # Validate total shift count per person
    if any(count < MIN_SHIFTS for count in person_shift_count.values()):
        print("less than min shifts", person_shift_count)
        return False

    # Validate consecutive shift rule (no more than 2 shifts in a row)
    if any(len(sequence) > MAX_CONSECUTIVE_SHIFTS for sequence in person_shift_sequence.values()):
        print("more than 2 consecutive shifts")
        return False

    # Validate consecutive leadership rule (leaders can't lead more than 2 weeks in a row)
    if any(len(sequence) > MAX_CONSECUTIVE_SHIFTS for sequence in leader_shift_sequence.values()):
        print("more than 2 consecutive leader shifts")
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
            valid = is_valid_assignment(assignment_dict)
            if not valid:
                return assign_shifts_backtracker(preference_dict, weeks)
            return valid

        current_week = weeks[index]

        # Sort participants randomly (shuffling before sorting)
        randomized_items = list(preference_dict.items())  # Convert items to a list
        random.shuffle(randomized_items)  # Shuffle the list in place

        # Sort participants by the number of shifts they've already been assigned to
        participants = sorted(randomized_items, key=lambda x: len([
            shift for week in assignment_dict.values()
            for shift in (week["setup"] + week["cleanup"]) if shift["name"] == x[0]
        ]))

        setup_leader_count = sum(1 for p in assignment_dict[current_week]["setup"] if p.get("leader_this_week"))
        cleanup_leader_count = sum(1 for p in assignment_dict[current_week]["cleanup"] if p.get("leader_this_week"))

        remaining_setup_leaders = REQUIRED_SETUP_LEADERS - setup_leader_count
        remaining_cleanup_leaders = REQUIRED_CLEANUP_LEADERS - cleanup_leader_count
        

        # Step 1: First, try to assign leaders to setup and cleanup
        for person, preferences in participants:
            person_shift_count, person_shift_sequence, leader_shift_sequence = track_person_shifts(assignment_dict)
            
            # Prevent double assignment in the same week (setup + cleanup)
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue
            
            if person_shift_count.get(person, 0) >= MAX_SHIFTS:
                continue
            
            if len(leader_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and leader_shift_sequence[person][-1] == (index - 1):
                continue

            # Assign to setup first (leaders only)
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP and \
                preferences["is_leader"] and remaining_setup_leaders > 0:
                    leader_this_week = True
                    assignment_dict[current_week]["setup"].append({
                        "name": person,
                        "is_leader": preferences["is_leader"],
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
                    if leader_this_week:
                        leader_last_week[person].pop()

                if preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) > 0:
                    assignment_dict[current_week]["cleanup"].pop()
                    if leader_this_week:
                        leader_last_week[person].pop()

        # Step 2: Once leaders are assigned, fill the remaining spots with non-leaders
        for person, preferences in participants:
            # person_shift_count, person_shift_sequence, leader_shift_sequence = track_person_shifts(assignment_dict)
            
            # Prevent double assignment in the same week
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue
            
            if person_shift_count.get(person, 0) >= MAX_SHIFTS:
                continue
            
            if len(person_shift_sequence.get(person, [])) >= MAX_CONSECUTIVE_SHIFTS and person_shift_sequence[person][-1] == (index - 1):
                continue

            # Assign to setup for non-leaders
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP:
                if not preferences["is_leader"]:
                    assignment_dict[current_week]["setup"].append({
                        "name": person,
                        "is_leader": preferences["is_leader"],
                        "leader_this_week": False
                    })

            # Assign to cleanup for non-leaders
            elif preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP:
                if not preferences["is_leader"]:
                    assignment_dict[current_week]["cleanup"].append({
                        "name": person,
                        "is_leader": preferences["is_leader"],
                        "leader_this_week": False
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
                else:
                    file.write(f"     {person['name']}\n")

            file.write("\n  Cleanup:\n")
            for person in shifts["cleanup"]:
                if person['leader_this_week']:
                    file.write(f"     {person['name']} (Leader)\n")
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
        file.write("First Name\tLast Name\tPreference\tLeader\tTotals\t" + "\t".join(all_weeks) + "\n")
        
        # Write each person's row of assignments
        for person, assignments in person_assignments.items():
            name_parts = person.split()
            first_name = name_parts[0]
            last_name = name_parts[-1]
            preference = preference_dict[person]['preference']
            leader_status = int(preference_dict[person]['is_leader'])
            total_shifts = assignments['setup'] + assignments['cleanup']

            # Prepare the row with the person's data
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
    if assignment_dict:
        save_assignments_to_week_file(assignment_dict, "week_schedule.txt")
        save_assignments_to_quarter_file(preference_dict, assignment_dict, weeks, "quarter_schedule.txt")
    else:
        print("No valid assignment found.")


if __name__ == "__main__":
    run()