package com.example.userservice;

import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.stereotype.Component;

@Component
public class DemoHealthState {

    private final AtomicBoolean healthy = new AtomicBoolean(true);

    public boolean isHealthy() {
        return healthy.get();
    }

    public void setHealthy(boolean value) {
        healthy.set(value);
    }
}
