FROM python:3.12-slim

WORKDIR /app

# Install bluetooth stack and Python bindings
RUN apt-get update && \
    apt-get install -y bluetooth bluez python3-bluez && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY bluetti_mqtt/ bluetti_mqtt/

ENTRYPOINT ["python", "-m", "bluetti_mqtt.server_cli"]

CMD []

# On the host: sudo apt install bluez
# Check bluetooth device is detected: hciconfig -a
# Run the container: docker run -p 9219:9219 -v /var/run/dbus:/var/run/dbus <Image> --prometheus xx:xx:xx:xx:xx:xx
