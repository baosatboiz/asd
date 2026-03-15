package com.example.userservice;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class DemoHealthIndicator implements HealthIndicator {

    private final DemoHealthState demoHealthState;

    public DemoHealthIndicator(DemoHealthState demoHealthState) {
        this.demoHealthState = demoHealthState;
    }

    @Override
    public Health health() {
        if (demoHealthState.isHealthy()) {
            return Health.up().withDetail("demoHealth", "UP").build();
        }
        return Health.down().withDetail("demoHealth", "DOWN").build();
    }
}
