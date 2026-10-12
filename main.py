import os

source_extensions = [
    ".py", ".java", ".c", ".cpp",
    ".js", ".html", ".css",
    ".php", ".ts"
]


folder_path = input("Enter project folder path: ")


summary = open("summary.txt", "w", encoding="utf-8")

summary.write("PROJECT SOURCE CODE SUMMARY\n")
summary.write("=" * 60 + "\n\n")

for root, folders, files in os.walk(folder_path):

    for file in files:

        extension = os.path.splitext(file)[1].lower()

        if extension not in source_extensions:
            continue

        full_path = os.path.join(root, file)

        try:
            f = open(full_path, "r", encoding="utf-8", errors="ignore")
            content = f.read().lower()
            f.close()

        except:
            content = ""

        description = ""

        if "main" in file.lower():
            description = "Contains the main entry point of the application."

        elif "login" in file.lower() or "auth" in file.lower():
            description = "Handles user authentication and login."

        elif "register" in file.lower():
            description = "Handles user registration."

        elif "database" in file.lower() or "db" in file.lower():
            description = "Handles database operations."

        elif "config" in file.lower():
            description = "Stores configuration settings."

        elif "helper" in file.lower() or "util" in file.lower():
            description = "Provides helper functions."

        elif "test" in file.lower():
            description = "Contains test cases."


        elif "import flask" in content:
            description = "Implements a Flask web application."

        elif "django" in content:
            description = "Part of a Django web application."

        elif "express" in content:
            description = "Implements an Express.js application."

        elif "sqlite3" in content:
            description = "Performs SQLite database operations."

        elif "mysql" in content:
            description = "Performs MySQL database operations."

        elif "select " in content or "insert " in content or "update " in content:
            description = "Contains SQL database queries."

        elif "class " in content:
            description = "Defines one or more classes."

        elif "def " in content:
            description = "Contains functions that implement program logic."

        elif "@app.route" in content:
            description = "Defines web routes."

        elif "<html" in content:
            description = "Creates the structure of a web page."

        elif "body {" in content or ".container" in content:
            description = "Defines the style of a web page."

        elif "function " in content:
            description = "Contains JavaScript functions."

        elif "print(" in content:
            description = "Contains program logic and output statements."

        else:
            description = "Contains source code for the application."

        summary.write(f"File Name : {file}\n")
        summary.write(f"Location  : {os.path.relpath(full_path, folder_path)}\n")
        summary.write(f"Purpose   : {description}\n")
        summary.write("-" * 60 + "\n")

summary.close()

print("\nAnalysis Completed Successfully!")
print("Summary saved as summary.txt")
