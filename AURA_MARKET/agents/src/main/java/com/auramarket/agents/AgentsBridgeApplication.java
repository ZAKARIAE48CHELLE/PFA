package com.auramarket.agents;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"com.auramarket.agents", "agents", "bridge"})
public class AgentsBridgeApplication {
    public static void main(String[] args) {
        SpringApplication.run(AgentsBridgeApplication.class, args);
    }
}
