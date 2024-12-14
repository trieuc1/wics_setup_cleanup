def parse_file(file) -> dict:
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


if __name__ == "__main__":
    file_name = "preference.txt"
    parse_file(file_name)