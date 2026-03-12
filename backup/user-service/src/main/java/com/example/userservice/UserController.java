package com.example.userservice;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    private final DemoHealthState demoHealthState;

    @Value("${server.port}")
    private String port;

    @Value("${spring.application.name}")
    private String serviceName;

    @Value("${eureka.instance.instance-id:unknown}")
    private String instanceId;

    @Value("${info.app.version:1.0.0}")
    private String version;

    public UserController(DemoHealthState demoHealthState) {
        this.demoHealthState = demoHealthState;
    }

    @GetMapping("/hello")
    public String hello() {
        return "Hello from instance " + port;
    }

    @GetMapping("/whoami")
    public Map<String, String> whoami() {
        Map<String, String> payload = new LinkedHashMap<>();
        payload.put("serviceName", serviceName);
        payload.put("instanceId", instanceId);
        payload.put("port", port);
        payload.put("version", version);
        payload.put("timestamp", Instant.now().toString());
        payload.put("healthMode", demoHealthState.isHealthy() ? "UP" : "DOWN");
        return payload;
    }

    @PostMapping("/admin/health/down")
    public Map<String, String> markDown() {
        demoHealthState.setHealthy(false);
        return Map.of("status", "DOWN");
    }

    @PostMapping("/admin/health/up")
    public Map<String, String> markUp() {
        demoHealthState.setHealthy(true);
        return Map.of("status", "UP");
    }
}
