package com.example.userservice;

import java.net.InetAddress;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    private final DemoHealthState demoHealthState;
    private final JdbcTemplate jdbcTemplate;

    @Value("${server.port}")
    private String port;

    @Value("${spring.application.name}")
    private String serviceName;

    @Value("${eureka.instance.instance-id:unknown}")
    private String instanceId;

    @Value("${info.app.version:1.0.0}")
    private String version;

    public UserController(DemoHealthState demoHealthState, JdbcTemplate jdbcTemplate) {
        this.demoHealthState = demoHealthState;
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/hello")
    public String hello() {
        return "Hello from instance " + port;
    }

    @GetMapping("/whoami")
    public Map<String, String> whoami() {
        String hostname;
        try {
            hostname = InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            hostname = "unknown";
        }
        Map<String, String> payload = new LinkedHashMap<>();
        payload.put("serviceName", serviceName);
        payload.put("instanceId", instanceId);
        payload.put("hostname", hostname);
        payload.put("port", port);
        payload.put("version", version);
        payload.put("timestamp", Instant.now().toString());
        payload.put("healthMode", demoHealthState.isHealthy() ? "UP" : "DOWN");
        return payload;
    }

    @GetMapping("/users")
    public List<Map<String, Object>> users() {
        return jdbcTemplate.queryForList("SELECT id, name, email FROM app_user ORDER BY id");
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
