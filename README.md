# Module fingerprint

Support for the Adafruit R503 fingerprint sensor, used to enroll and match fingerprints via UART.

## Model joyce:fingerprint:adafruit-r503

This model enables control of the Adafruit R503 fingerprint sensor through a Viam module. It supports enrollment, matching, and deletion of fingerprint templates. LED control is also available for visual feedback during interactions.

### Configuration

The following attribute template can be used to configure this model:

```json
{
"attribute_1": <string>
}
```

#### Attributes

The following attributes are available for this model:

| Name          | Type   | Inclusion | Description                                                                                                                           |
| ------------- | ------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `serial_port` | string | Optional  | The serial device path (e.g., `/dev/ttyUSB0`). If not provided, the module will default to the first available `/dev/ttyUSB*` device. |

#### Example Configuration

```json
{
  "serial_port": "/dev/ttyUSB0"
}
```
