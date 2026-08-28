import uvicorn

from jinrong.config.settings import settings

if __name__ == '__main__':
    uvicorn.run(app='jinrong.api.app:app', host=settings.app_host, port=settings.app_port)
