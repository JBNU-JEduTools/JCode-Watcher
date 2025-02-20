

# class FileSize(BaseModel):
#     bytes: int
# 
# @app.post("/api/{class_div}/{hw_name}/{student_id}/{filename}/{timestamp}")
# async def register_snapshot(
#     class_div: str,
#     hw_name: str,
#     student_id: str,
#     filename: str,
#     timestamp: str,
#     file_size: FileSize = Body(...),
# ):
#     return {
#         "class_div": class_div,
#         "hw_name": hw_name,
#         "student_id": student_id,
#         "filename": filename,
#         "timestamp": timestamp,
#         "bytes": file_size.bytes,
#     }