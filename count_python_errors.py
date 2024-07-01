import subprocess
from collections import Counter

# Run ruff and capture the output
result = subprocess.run(['ruff', 'check', '.'], stdout=subprocess.PIPE, text=True)

# Split the output into lines
lines = result.stdout.splitlines()

# Extract the filenames from the output
filenames = [line.split(':')[0] for line in lines]

# Count the occurrences of each filename
file_error_counts = Counter(filenames)

# Calculate the total count of errors
total_errors = sum(file_error_counts.values())



for filename, count in file_error_counts.items():
    print(f'{filename}: {count} errors')
print(f'Total number of errors: {total_errors}')
