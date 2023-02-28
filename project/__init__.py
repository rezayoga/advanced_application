from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    from project.orders import orders_router  # new
    app.include_router(orders_router)  # new

    @app.get("/")
    async def root():
        return {"message": "Hello Python"}

    return app
