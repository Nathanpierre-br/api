from fastapi.responses import JSONResponse


class TurtleAnswers:
    @staticmethod
    def OK():
        return JSONResponse({"status": "OK", "comment": "Have a good day, sir."})

    @staticmethod
    def ERR(comment: str):
        return JSONResponse(
            {"status": "ERR", "comment": comment},
            status_code=400,
        )
