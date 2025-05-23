# Module fingerprint

Support for the Adafruit R503 fingerprint sensor, used to enroll and match fingerprints via UART.

## Model joyce:fingerprint:adafruit-r503

This model enables control of the Adafruit R503 fingerprint sensor through a Viam module. It supports enrollment, matching, and deletion of fingerprint templates. LED control is also available for visual feedback during interactions.

### Configuration

The following attribute template can be used to configure this model:

```json
{
"serial_port": <string>
}
```

#### Attributes

The following attributes are available for this model:

| Name          | Type   | Inclusion | Description                                                                                                                                                                                                                                     |
| ------------- | ------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `serial_port` | string | Optional  | The serial device path (e.g., `/dev/ttyUSB0`). If not provided, the module will default to the first available `/dev/ttyUSB*` device. To determine the correct port, run `ls /dev/ttyUSB*` on your Pi to list all connected USB serial devices. |

#### Example Configuration

```json
{
  "serial_port": "/dev/ttyUSB0"
}
```

### DoCommand

An example payload of each command that is supported and the arguments that can be used.

#### Example DoCommand

```json
{ "reset_enrollment": true }
```

Begin enrollment process (to capture two scans of fingerprint). This library is designed to work with two scans per enrollment slot (slot `1` shown here). You can optionally add more slots to enroll variations of the same print for higher reliability in finding a match, for example by scanning the edges of the fingerprint in subsequent enrollment slots.

```json
{ "start_enrollment": 1 }
```

Hold the finger on the sensor, and scan the first print.

```json
{ "capture": true }
```

Hold the finger on the sensor, and scan the second print. Retry this step until two successful scans are completed.

```json
{ "capture": true }
```

Retry the previous step until two successful scans are completed. Then create a new model.

```json
{ "create_model": true }
```

Upon successfully creating a model, store the model using the enrollment slot defined earlier (slot `1` shown here).

```json
{ "store_model": 1 }
```

Other example DoCommands include:

```json
{ "match_fingerprint": true }
```

```json
{ "test_led": true }
```
