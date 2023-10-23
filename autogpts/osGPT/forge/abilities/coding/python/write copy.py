# from ...registry import ability
# from ...schema import AbilityResult
# from ....schema import Project, Issue, Attachment, AttachmentUploadActivity, AttachmentUpdateActivity, Comment
# from forge.sdk import ForgeLogger

# logger = ForgeLogger(__name__)

# @ability(
#     name="write_code",
#     description="Create or update a Python file with the provided content in the workspace.",
#     parameters=[
#         {
#             "name": "file_name",
#             "description": "Name of the Python file to be created or updated.",
#             "type": "string",
#             "required": True,
#         },
#         {
#             "name": "content",
#             "description": "Content to be written to the Python file.",
#             "type": "string",
#             "required": True,
#         },
#     ],
#     output_type="object",
# )
# async def write_code(
#     agent, project: Project, issue: Issue, file_name: str, content: str
# ) -> AbilityResult:
#     """
#     Create or update a Python file and write the provided content to it.
#     A code review will be initiated for new files only.
#     """
#     # Ensure the file_name ends with '.py'
#     if not file_name.endswith(".py"):
#         file_name += ".py"

#     project_root = agent.workspace.get_project_path_by_key(project.key)
#     file_path = project_root / file_name

#     # Determine if the file already exists
#     existing_files = agent.workspace.list_files_by_key(key=project.key, path=file_path.parent)
#     existing_file = next((f for f in existing_files if f['filename'] == file_name), None)

#     # Write the content to the file
#     if isinstance(content, str):
#         content = content.encode()

#     file_info = agent.workspace.write_file_by_key(
#         key=project.key, path=file_path, data=content
#     )

#     new_attachment = Attachment(
#         url=file_info["relative_url"],
#         filename=file_info["filename"],
#         filesize=file_info["filesize"],
#     )

#     # Determine the appropriate activity and comment based on whether the file already exists
#     if existing_file:
#         old_attachment = Attachment(
#             url=existing_file["relative_url"],
#             filename=existing_file["filename"],
#             filesize=existing_file["filesize"],
#         )
#         update_activity = AttachmentUpdateActivity(created_by=agent, old_attachment=old_attachment, new_attachment=new_attachment)
#         comment_content = f"The file '{file_name}' has been updated."
#     else:
#         update_activity = AttachmentUploadActivity(created_by=agent, attachment=new_attachment)
#         comment_content = f"A new file '{file_name}' has been created.  I'll test it for alignment with the requirements and report back shortly."

#     # Update the issue with the activity and the attachment
#     issue.add_activity(update_activity)
#     issue.add_attachment(new_attachment)

#     # Add a comment indicating the status of the code and if a review is being initiated
#     comment = Comment(
#         created_by=agent,
#         content=comment_content,
#         attachments=[new_attachment],
#     )
#     issue.add_activity(comment)

#     return AbilityResult(
#         ability_name="write_code",
#         ability_args={"file_name": file_name, "content": content},
#         success=True,
#         activities=[update_activity, comment],
#         attachments=[new_attachment],
#     )
