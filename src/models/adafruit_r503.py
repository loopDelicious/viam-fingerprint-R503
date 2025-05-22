from typing import (Any, ClassVar, Dict, List, Mapping, Optional,
                    Sequence)
import time
import serial
from PIL import Image
import adafruit_fingerprint
import glob
import os

from typing_extensions import Self
from viam.components.sensor import *
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, ValueTypes
from viam.logging import getLogger

LOGGER = getLogger("fingerprint-sensor")

class AdafruitR503(Sensor, EasyResource):
    MODEL: ClassVar[Model] = Model(ModelFamily("joyce", "fingerprint"), "adafruit-r503")

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        instance = super().new(config, dependencies)
        instance._reset_enrollment_state()
        return instance

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any implicit dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Sequence[str]: A list of implicit dependencies
        """

        errors = []

        serial_field = config.attributes.fields.get("serial_port")
        if serial_field and serial_field.WhichOneof("kind") != "string_value":
            errors.append("serial_port must be a string")

        return errors

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both implicit and explicit)
        """
        serial_field = config.attributes.fields.get("serial_port")

        if serial_field and serial_field.WhichOneof("kind") == "string_value":
            self.serial_port = serial_field.string_value
        else:
            ports = sorted(glob.glob("/dev/ttyUSB*"))
            if ports:
                self.serial_port = ports[0]
            else:
                raise RuntimeError("No available serial ports found (e.g., /dev/ttyUSB0) and no serial_port was provided in config.")

        return super().reconfigure(config, dependencies)

    def _enroll_finger(self, location: int) -> bool:
        for fingerimg in range(1, 3):
            prompt = "Place finger on sensor..." if fingerimg == 1 else "Place same finger again..."
            LOGGER.info(prompt)

            while True:
                i = self.finger.get_image()
                if i == adafruit_fingerprint.OK:
                    LOGGER.info("Image taken")
                    break
                if i == adafruit_fingerprint.NOFINGER:
                    time.sleep(0.1)
                elif i == adafruit_fingerprint.IMAGEFAIL:
                    LOGGER.error("Imaging error")
                    return False
                else:
                    LOGGER.error("Other error")
                    return False

            LOGGER.info("Templating...")
            i = self.finger.image_2_tz(fingerimg)
            if i != adafruit_fingerprint.OK:
                LOGGER.warning("Failed to template image")
                return False

            if fingerimg == 1:
                LOGGER.info("Remove finger")
                time.sleep(1)
                while self.finger.get_image() != adafruit_fingerprint.NOFINGER:
                    time.sleep(0.1)

        LOGGER.info("Creating model...")
        if self.finger.create_model() != adafruit_fingerprint.OK:
            LOGGER.warning("Fingerprints did not match")
            return False

        LOGGER.info(f"Storing model #{location}...")
        if self.finger.store_model(location) != adafruit_fingerprint.OK:
            LOGGER.warning("Failed to store model")
            return False

        return True

    def _save_fingerprint_image(self, filename: str) -> bool:
        while self.finger.get_image() != adafruit_fingerprint.OK:
            time.sleep(0.1)

        img = Image.new("L", (256, 288), "white")
        pixeldata = img.load()
        mask = 0b00001111
        result = self.finger.get_fpdata(sensorbuffer="image")

        x, y = 0, 0
        for byte in result:
            pixeldata[x, y] = ((byte >> 4) & mask) * 17
            x += 1
            pixeldata[x, y] = (byte & mask) * 17
            if x == 255:
                x = 0
                y += 1
            else:
                x += 1

        try:
            img.save(filename)
            return True
        except Exception as e:
            LOGGER.error(f"Failed to save image: {e}")
            return False
        
    def _ensure_finger_initialized(self):
        if not hasattr(self, "finger"):
            uart = serial.Serial(self.serial_port, baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
            try:
                self.finger.set_led(color=1, mode=4)  # Turn off LED at init
            except Exception as e:
                self.logger.warning(f"Failed to turn off LED after init: {e}")

    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, Any]:
        self.logger.debug("Getting readings from the sensor")
        self._ensure_finger_initialized()

        # Flash purple breathing to show sensor startup
        if not hasattr(self, "_did_purple_breathe"):
            self.finger.set_led(color=3, mode=1)
            time.sleep(3)
            self.finger.set_led(color=1, mode=4)
            self._did_purple_breathe = True

        try:
            # Step 1: Check for finger
            i = self.finger.get_image()
            if i != adafruit_fingerprint.OK:
                self.finger.set_led(color=0, mode=4)  # LED off
                return {"finger_detected": False}

            # Step 2: Convert image to template
            i = self.finger.image_2_tz(1)
            if i != adafruit_fingerprint.OK:
                self.finger.set_led(color=1, mode=2, speed=100)  # Red flash on bad template
                return {"finger_detected": True, "matched": False}

            # Step 3: Search for match
            i = self.finger.finger_search()
            if i != adafruit_fingerprint.OK:
                self.finger.set_led(color=1, mode=2, speed=100)  # Red flash
                return {"finger_detected": True, "matched": False}

            # Step 4: Show match with green (or blue/purple) flash
            self.finger.set_led(color=2, mode=2, speed=100)  # Blue flash
            return {
                "finger_detected": True,
                "matched": True,
                "matched_id": int(self.finger.finger_id),
                "confidence": int(self.finger.confidence),
            }

        except Exception as e:
            self.logger.error(f"Fingerprint error: {str(e)}")
            return {
                "finger_detected": False,
                "error": str(e)
            }

    def _reset_enrollment_state(self):
        """Reset enrollment tracking variables."""
        self._enrollment_step = None
        self._enrollment_id = None
        self._enrollment_active = False

    def _begin_enrollment(self, slot: int) -> str:
        """Begin enrollment process and initialize state."""
        self._enrollment_id = slot
        self._enrollment_step = 1
        self._enrollment_active = True
        return f"Enrollment started for slot {slot}. Place your finger on the sensor."

    def _enrollment_capture_step(self) -> str:
        if not self._enrollment_active or self._enrollment_id is None:
            return "Enrollment not active. Run 'start_enrollment' first."

        self.finger.set_led(color=2, mode=1) # Breathing blue for readiness

        i = self.finger.get_image()
        if i != adafruit_fingerprint.OK:
            self.finger.set_led(color=1, mode=1)  # Flash red
            return f"Error capturing image: {i}"

        i = self.finger.image_2_tz(self._enrollment_step)
        if i != adafruit_fingerprint.OK:
            self.finger.set_led(color=1, mode=1)  # Flash red
            return f"Error templating image at step {self._enrollment_step}: {i}"

        self.finger.set_led(color=1, mode=4)

        msg = f"Step {self._enrollment_step} completed."

        if self._enrollment_step == 1:
            self._enrollment_step = 2
            msg += " Remove finger and place again for step 2."
        else:
            msg += " Both scans captured. Call 'create_model'."

        return msg

    def _enrollment_create_model(self) -> str:
        """Create fingerprint model from two scans."""
        if not self._enrollment_active:
            return "Enrollment not active."

        i = self.finger.create_model()
        if i != adafruit_fingerprint.OK:
            return f"Error creating model: {i}"
        return "Model created. You can now run 'store_model' to save it."

    def _enrollment_store_model(self, slot: int) -> str:
        """Store the created model in given slot."""
        if not self._enrollment_active:
            return "Enrollment not active."

        i = self.finger.store_model(slot)
        if i != adafruit_fingerprint.OK:
            return f"Error storing model at slot {slot}: {i}"

        self._reset_enrollment_state()
        return f"Model stored successfully at slot {slot}."

    def _match_fingerprint(self) -> dict:
        self._ensure_finger_initialized()

        # Turn on purple breathing to show scan in progress
        self.finger.set_led(color=3, mode=1)  # Purple breathe

        i = self.finger.get_image()
        if i != adafruit_fingerprint.OK:
            self._flash_led(color=1)  # Red flash for no finger
            return {"status": "no_finger"}

        i = self.finger.image_2_tz(1)
        if i != adafruit_fingerprint.OK:
            self._flash_led(color=1)  # Red flash for bad template
            return {"status": "template_failed", "code": i}

        i = self.finger.finger_search()
        if i != adafruit_fingerprint.OK:
            self._flash_led(color=1)  # Red flash for no match
            return {"status": "no_match"}

        self._flash_led(color=2)  # Green flash on match
        return {
            "status": "match",
            "matched_id": self.finger.finger_id,
            "confidence": self.finger.confidence,
        }
    
    def _flash_led(self, color: int = 3):
        try:
            self.finger.set_led(color=color, mode=2, speed=100)  # Flash visibly
            time.sleep(0.5)
            self.finger.set_led(color=1, mode=4)  # Turn off LED
        except Exception as e:
            self.logger.warning(f"LED flash failed: {e}")

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        self._ensure_finger_initialized()
        result = {}

        for name, value in command.items():
            if name == "start_enrollment":
                self._reset_enrollment_state()
                self._enrollment_id = int(value)
                self._enrollment_step = 1
                self._enrollment_active = True
                result["message"] = f"Enrollment started at slot {self._enrollment_id}. Place finger for scan 1."

            elif name == "capture":
                if not self._enrollment_active or self._enrollment_step not in [1, 2]:
                    result["error"] = "Enrollment not started or invalid step"
                    continue

                # Run templating for current step
                msg = self._enrollment_capture_step()
                result["message"] = msg

                # Ensure step stays at 2 (max)
                if self._enrollment_step == 1:
                    self._enrollment_step = 2

            elif name == "create_model":
                if not self._enrollment_active:
                    result["error"] = "Enrollment not active"
                    continue

                msg = self._enrollment_create_model()
                if "Error" in msg or "did not match" in msg:
                    result["message"] = msg
                    result["rescan_required"] = True
                    # Stay at step 2 so the student can re-capture
                    self._enrollment_step = 2
                else:
                    result["message"] = msg

            elif name == "store_model":
                if not self._enrollment_active:
                    result["error"] = "Enrollment not active"
                    continue

                slot = int(value)
                msg = self._enrollment_store_model(slot)
                if msg.startswith("Error"):
                    result["error"] = msg
                else:
                    result["message"] = msg

            elif name == "reset_enrollment":
                self._reset_enrollment_state()
                result["message"] = "Enrollment state reset."

            elif name == "match_fingerprint":
                LOGGER.info("Matching fingerprint...")
                match = self._match_fingerprint()
                result.update(match)

            elif name == "delete_model":
                slot = int(value)
                i = self.finger.delete_model(slot)
                if i == adafruit_fingerprint.OK:
                    result["message"] = f"Deleted fingerprint at slot {slot}"
                else:
                    result["error"] = f"Failed to delete slot {slot}: code {i}"

            elif name == "list_templates":
                if self.finger.read_templates() != adafruit_fingerprint.OK:
                    result["error"] = "Failed to read templates"
                else:
                    result["templates"] = self.finger.templates

            elif name == "count_templates":
                if self.finger.count_templates() != adafruit_fingerprint.OK:
                    result["error"] = "Failed to count templates"
                else:
                    result["count"] = self.finger.template_count

            elif name == "test_led":
                try:
                    if value is True:
                        self.finger.set_led(color=3, mode=1)
                        result["message"] = "LED turned on (purple breathing)"
                    else:
                        self.finger.set_led(color=0, mode=4)
                        result["message"] = "LED turned off"
                except Exception as e:
                    result["error"] = f"LED test failed: {e}"
     
            else:
                result["error"] = f"Unknown command: {name}"

        return result

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[Geometry]:
        self.logger.error("`get_geometries` is not implemented")
        raise NotImplementedError()

