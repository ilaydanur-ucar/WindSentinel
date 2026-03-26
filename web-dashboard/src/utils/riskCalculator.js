/**
 * Pure risk calculation function - shared between Dashboard quick card and Measurement page.
 * No UI dependencies, no side effects.
 */
export function calculateRisk({ wind_speed, power_output, generator_rpm, gearbox_oil_temp, vibration }) {
  const ws = parseFloat(wind_speed) || 0;
  const po = parseFloat(power_output) || 0;
  const rpm = parseFloat(generator_rpm) || 0;
  const temp = parseFloat(gearbox_oil_temp) || 0;
  const vib = parseFloat(vibration) || 0;

  const expectedPower = ws > 3 ? Math.min(ws * ws * ws * 0.0005, 3.0) : 0;
  const powerDeviation = Math.abs(po - expectedPower) / (expectedPower + 0.1);

  const expectedRpm = ws > 3 ? ws * 120 : 0;
  const rpmDeviation = rpm > 0 ? Math.abs(rpm - expectedRpm) / (expectedRpm + 1) : 0;

  const tempRisk = temp > 80 ? 0.9 : temp > 65 ? 0.5 : temp > 50 ? 0.2 : 0.05;
  const vibRisk = vib > 6 ? 0.95 : vib > 3 ? 0.5 : vib > 1.5 ? 0.15 : 0.03;

  const riskScore = Math.min(100, Math.round(
    (powerDeviation * 25 + rpmDeviation * 20 + tempRisk * 100 * 0.3 + vibRisk * 100 * 0.25)
  ));

  return {
    riskScore,
    powerDeviation: (powerDeviation * 100).toFixed(1),
    tempRisk: (tempRisk * 100).toFixed(0),
    vibRisk: (vibRisk * 100).toFixed(0),
  };
}
