import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "studio.api:create_app",
        factory=True,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
