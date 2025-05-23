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

This module supports several commands for fingerprint enrollment, matching, template management, and LED testing. Each command can be triggered using a **DO COMMAND** request with a corresponding JSON payload, under the **CONTROL** tab of the Viam app.

Below are all supported payloads and their usage.

#### Example DoCommand

The enrollment process captures two fingerprint scans and stores them to a slot in memory.

**Start enrollment**:

```json
{ "start_enrollment": 1 }
```

Begins enrollment for slot `1`. Replace `1` with any unused slot number. The sensor will now wait for fingerprint scans.

**Capture scans**:

```json
{ "capture": true }
```

Call this twice:

1. First with finger pressed on the sensor.
1. Then remove and re-place the same finger for the second scan.

If there’s an issue (e.g. misaligned finger), repeat this step. The enrollment state tracks progress automatically.

**Create fingerprint model**:

```json
{ "create_model": true }
```

Attempts to create a model from the two captured scans. If the prints don't match, it will prompt to retry the second scan (capture again).

**Store model**:

```json
{ "store_model": 1 }
```

Stores the created model in slot `1` (or the slot used in start_enrollment). You can enroll the same fingerprint multiple times in different slots to improve match reliability under varying finger angles or pressure.

**Reset enrollment state**:

```json
{ "reset_enrollment": true }
```

Clears the current enrollment process. Useful for recovering from a bad scan sequence.

**Match fingerprint**:

```json
{ "match_fingerprint": true }
```

Attempts to read and match a fingerprint against the enrolled models.

**Delete a template**:

```json
{ "delete_model": 1 }
```

Deletes the fingerprint stored in slot `1`.

**List enrolled templates**:

```json
{ "list_templates": true }
```

Returns the list of currently enrolled slot numbers.

**Count enrolled templates**:

```json
{ "count_templates": true }
```

Returns the total number of templates stored on the sensor.

**Test the LED**:

```json
{ "test_led": true }
```

Turns on the LED in test mode.

```json
{ "test_led": false }
```

Turns off the LED.
