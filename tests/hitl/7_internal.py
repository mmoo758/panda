import time
import pytest

from panda import Panda

pytestmark = [
  pytest.mark.test_panda_types(Panda.INTERNAL_DEVICES),
]

MAX_RPM = 5000

@pytest.mark.timeout(2*60)
def test_fan_controller(p):
  start_health = p.health()

  rpms = []
  for power in (30, 70, 100):
    # wait until fan spins up
    p.set_fan_power(power)
    for _ in range(20):
      time.sleep(1)
      if p.get_fan_rpm() > 1000:
        break
    time.sleep(2)  # wait for RPM to converge
    rpms.append(p.get_fan_rpm())

  print(rpms)
  diffs = [b - a for a, b in zip(rpms, rpms[1:])]
  assert all(x > 0 for x in diffs), f"Fan RPMs not strictly increasing: {rpms=}"
  assert rpms[-1] > (0.75*MAX_RPM)

  # Ensure the stall detection is tested on dos
  if p.get_type() == Panda.HW_TYPE_DOS:
    stalls = p.health()['fan_stall_count'] - start_health['fan_stall_count']
    assert stalls >= 2
    print("stall count", stalls)
  else:
    assert p.health()['fan_stall_count'] == 0

def test_fan_cooldown(p):
  # if the fan cooldown doesn't work, we get high frequency noise on the tach line
  # while the rotor spins down. this makes sure it never goes beyond the expected max RPM
  p.set_fan_power(100)
  time.sleep(3)
  p.set_fan_power(0)
  for _ in range(5):
    assert p.get_fan_rpm() <= MAX_RPM*2
    time.sleep(0.5)

def test_fan_overshoot(p):
  if p.get_type() == Panda.HW_TYPE_DOS:
    pytest.skip("panda's fan controller overshoots on the comma three fans that need stall recovery")

  # make sure it's stopped completely
  p.set_fan_power(0)
  while p.get_fan_rpm() > 0:
    time.sleep(0.1)

  # set it to 30% power to mimic going onroad
  p.set_fan_power(30)
  max_rpm = 0
  for _ in range(50):
    max_rpm = max(max_rpm, p.get_fan_rpm())
    time.sleep(0.1)

  # tolerate 10% overshoot
  expected_rpm = MAX_RPM*2 * 30 / 100
  assert max_rpm <= 1.1 * expected_rpm, f"Fan overshoot: {(max_rpm / expected_rpm * 100) - 100:.1f}%"
