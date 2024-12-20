MIN_SETUP = 7
MIN_CLEANUP = 5
MIN_LEADERS = 1
MAX_SHIFTS = 5

def parse_file(file : str) -> dict:
    with open(file, 'r') as file:
        preference_dict = {}
        for line in file:
            parts = line.split()
            name = []
            shift_preference = ""
            is_leader = parts[-1] == '1'
            for part in parts:
                if part not in ['s', 'c', 's/c', '-'] and not part.isdigit():
                    name.append(part)
                elif part in ['s', 'c', 's/c', '-']:
                    shift_preference = part
            name = " ".join(name)
            preference_dict[name] = {"preference" : shift_preference, "is_leader": is_leader}
        return preference_dict
    return None

def is_valid_assignment(assignment_dict: dict) -> bool:
    """
    Returns whether an assignment is valid or not.

    Criteria:
    - Each person has fewer than 5 shifts.
    - Each shift (setup and cleanup) has at least one leader.
    - Each week has:
        - At least 7 people in the setup group.
        - At least 5 people in the cleanup group.
    """
    # Dictionary to track the total number of shifts per person
    person_shift_count = {}
    
    for week, shifts in assignment_dict.items():
        # Validate setup group
        setup_group = shifts.get("setup", [])
        if len(setup_group) < MIN_SETUP:
            return False
        if sum(1 for person in setup_group if person["is_leader"]) < MIN_LEADERS:
            return False

        # Validate cleanup group
        cleanup_group = shifts.get("cleanup", [])
        if len(cleanup_group) < MIN_CLEANUP:
            return False
        if sum(1 for person in cleanup_group if person["is_leader"]) < MIN_LEADERS:
            return False

        # Update the total shift count for each person
        for person in setup_group + cleanup_group:
            name = person["name"]
            person_shift_count[name] = person_shift_count.get(name, 0) + 1

    # Validate shift count per person

    if any(count > MAX_SHIFTS for count in person_shift_count.values()):
        return False

    return True
    

def assign_shifts_backtracker(preference_dict: dict, weeks: list) -> dict:
    """
    Main function to assign shifts using backtracking with constraints.
    Ensures one setup and one cleanup shift per week.
    
    :param preference_dict: Dictionary containing people's preferences and leader status.
    :param weeks: List of weeks (e.g., ["Week 1", "Week 2", ...]).
    :return: Dictionary of valid shift assignments or None if no valid assignment exists.
    """
    assignment_dict = {week: {"setup": [], "cleanup": []} for week in weeks}
    person_last_week = {}

    def backtracking_helper(index: int) -> bool:
        """
        Recursive helper for backtracking with constraints:
        - Fill each week completely (5 cleanup, 7 setup) before moving to the next.
        - Avoid assigning participants to more than two consecutive weeks.
        - Ensure each participant is assigned to either cleanup or setup per week, not both.

        :param index: Current week index.
        :return: True if a valid assignment is found, False otherwise.
        """
        if index == len(weeks):
            return is_valid_assignment(assignment_dict)  # All weeks are filled

        current_week = weeks[index]

        # Sort participants by the number of shifts they already have to balance assignments
        participants = sorted(preference_dict.items(), key=lambda x: len([shift for week in assignment_dict.values() for shift in (week["setup"] + week["cleanup"]) if shift["name"] == x[0]]))

        for person, preferences in participants:
            # Avoid assigning the same person to more than two consecutive weeks
            last_two_weeks = [person_last_week.get(person, -1) == index - 1, person_last_week.get(person, -1) == index - 2]
            if sum(last_two_weeks) >= 2:
                continue

            # Ensure the person is not already assigned to another role this week
            if any(person == p["name"] for p in (assignment_dict[current_week]["setup"] + assignment_dict[current_week]["cleanup"])):
                continue

            # Try assigning the person to setup if their preference allows and setup is not full
            if preferences["preference"] in ["s", "s/c"] and len(assignment_dict[current_week]["setup"]) < MIN_SETUP:
                assignment_dict[current_week]["setup"].append({
                    "name": person,
                    "is_leader": preferences["is_leader"]
                })
                person_last_week[person] = index

                # Recursively assign remaining participants for the current week
                if backtracking_helper(index if len(assignment_dict[current_week]["setup"]) < MIN_SETUP or len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP else index + 1):
                    return True

                # Backtrack
                assignment_dict[current_week]["setup"].pop()
                if person_last_week.get(person) == index:
                    del person_last_week[person]

            # Try assigning the person to cleanup if their preference allows and cleanup is not full
            if preferences["preference"] in ["c", "s/c"] and len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP:
                assignment_dict[current_week]["cleanup"].append({
                    "name": person,
                    "is_leader": preferences["is_leader"]
                })
                person_last_week[person] = index

                # Recursively assign remaining participants for the current week
                if backtracking_helper(index if len(assignment_dict[current_week]["setup"]) < MIN_SETUP or len(assignment_dict[current_week]["cleanup"]) < MIN_CLEANUP else index + 1):
                    return True

                # Backtrack
                assignment_dict[current_week]["cleanup"].pop()
                if person_last_week.get(person) == index:
                    del person_last_week[person]

        return False
    
    if backtracking_helper(0):
        return assignment_dict


def save_assignments_to_file(assignments_by_week: dict, output_file: str) -> None:
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
                file.write(f"    - {person['name']} (Leader: {person['is_leader']})\n")

            file.write("\n  Cleanup:\n")
            for person in shifts["cleanup"]:
                file.write(f"    - {person['name']} (Leader: {person['is_leader']})\n")

            file.write("\n\n" + "-" * 50 + "\n\n")

    print(f"Assignments saved to {output_file}")

def run():
    file_name = "preferences.txt"
    weeks = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7"]
    preference_dict = parse_file(file_name)
    if sum(1 for v in preference_dict.values() if v["is_leader"]) < len(weeks):
        raise ValueError("Not enough leaders to assign at least one per week.")
    assignment_dict = assign_shifts_backtracker(preference_dict, weeks)
    if assignment_dict:
        save_assignments_to_file(assignment_dict, "output.txt")
    else:
        print("No valid assignment found.")


if __name__ == "__main__":
    run()