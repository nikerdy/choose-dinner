FROM python:3.9-slim

ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 安裝所需的Python包
RUN pip install --no-cache-dir flask line-bot-sdk pytz

# 複製Python腳本到容器中
COPY app.py .

# 暴露端口5000供webhook使用
EXPOSE 5000

# 運行Python腳本
CMD ["python", "app.py"]
