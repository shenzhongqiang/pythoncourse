def print_name(filename):
    with open(filename, "r") as f:
        content = f.read()
        lines = content.split("\n")
        for line in lines:
            if line:
                parts = line.split(",")
                print(parts[0])

print_name("contacts.txt")
