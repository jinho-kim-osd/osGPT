[
    {
        "role": "system",
        "content": "I want you to act as a Project Manager in Jira.\nYou'll be provided with the issue ID and the current status of the project, your task is to perform functions leading to the closure of the issue.\nYour role is limited to executing functions - refrain from providing explanations or issuing commands unless explicitly instructed.\nEnsure every required step is meticulously validated; only then are you to comment that the task is completed and update the status to 'Closed'.\nWhen communication in English is necessary, it will be facilitated by enclosing text within curly brackets {like this}.",
    },
    {
        "role": "user",
        "content": "Issue ID: 1\n\n📁 Project Arena Hacks Challenge 2023 (Key: AHC, Leader: Norman Osborn)\n    👤 Members:\n        Norman Osborn (Role: Administrator)\n        Max Dillon (Role: Member)\n        Jiyeon Lee (Role: Member)\n    📋 Task Issue #1: Sort the input.csv by the 'timestamp' column and write the new csv in the output.csv file. The\n    order of the columns should be preserved. (Status: Resolved, Assignee: Norman Osborn)\n        📆 Activities:\n            Norman Osborn created the Issue. just now\n            Norman Osborn added an Attachment: 'input.csv'. just now\n            Norman Osborn changed the Status Open → In Progress. just now\n            Norman Osborn changed the Assignee from Norman Osborn to Max Dillon. just now\n            Max Dillon added an Attachment: 'output.csv'. just now\n            Norman Osborn changed the Status In Progress → Resolved. just now\n        📎 Attachments:\n            File: input.csv, Uploaded at: 2023-10-21 16:30:10\n            File: output.csv, Uploaded at: 2023-10-21 16:30:28",
    },
    {"role": "user", "content": "Use functions only."},
    {
        "role": "function",
        "name": "read_file",
        "content": "[Success] read_file: id,name,timestamp\n1,Bob,2023-09-24 12:05:00\n2,Charlie,2023-09-24 12:10:00\n3,Alice,2023-09-25 14:10:00\n4,David,2023-09-26 16:20:00\n",
    },
    {
        "role": "assistant",
        "name": "read_file",
        "content": "Based on the results from the executed function, I'll proceed with the next appropriate actions.",
    },
    {
        "role": "user",
        "content": "Issue ID: 1\n📁 Project Arena Hacks Challenge 2023 (Key: AHC, Leader: Norman Osborn)\n    👤 Members:\n        Norman Osborn (Role: Administrator)\n        Max Dillon (Role: Member)\n        Jiyeon Lee (Role: Member)\n    📋 Task Issue #1: Sort the input.csv by the 'timestamp' column and write the new csv in the output.csv file. The\n    order of the columns should be preserved. (Status: Resolved, Assignee: Norman Osborn)\n        📆 Activities:\n            Norman Osborn created the Issue. just now\n            Norman Osborn added an Attachment: 'input.csv'. just now\n            Norman Osborn changed the Status Open → In Progress. just now\n            Norman Osborn changed the Assignee from Norman Osborn to Max Dillon. just now\n            Max Dillon added an Attachment: 'output.csv'. just now\n            Norman Osborn changed the Status In Progress → Resolved. just now\n        📎 Attachments:\n            File: input.csv, Uploaded at: 2023-10-21 16:30:10\n            File: output.csv, Uploaded at: 2023-10-21 16:30:28",
    },
    {
        "role": "user",
        "content": "📁 Project Arena Hacks Challenge 2023 (Key: AHC, Leader: Norman Osborn)\n    👤 Members:\n        Norman Osborn (Role: Administrator)\n        Max Dillon (Role: Member)\n        Jiyeon Lee (Role: Member)\n    📋 Task Issue #1: Sort the input.csv by the 'timestamp' column and write the new csv in the output.csv file. The\n    order of the columns should be preserved. (Status: Resolved, Assignee: Norman Osborn)\n        📆 Activities:\n            Norman Osborn created the Issue. just now\n            Norman Osborn added an Attachment: 'input.csv'. just now\n            Norman Osborn changed the Status Open → In Progress. just now\n            Norman Osborn changed the Assignee from Norman Osborn to Max Dillon. just now\n            Max Dillon added an Attachment: 'output.csv'. just now\n            Norman Osborn changed the Status In Progress → Resolved. just now\n        📎 Attachments:\n            File: input.csv, Uploaded at: 2023-10-21 16:30:10\n            File: output.csv, Uploaded at: 2023-10-21 16:30:28",
    },
]
