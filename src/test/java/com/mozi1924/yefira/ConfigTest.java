package com.mozi1924.yefira;

import com.mozi1924.yefira.config.YefiraConfig;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class ConfigTest {

    @Test
    public void testConfigDefaultsAndSetters() {
        YefiraConfig config = new YefiraConfig();

        Assertions.assertEquals("0.0.0.0", config.getHost());
        Assertions.assertEquals(8765, config.getPort());
        Assertions.assertFalse(config.isAutoStartOnWorldLoad());
        Assertions.assertFalse(config.isEnableLegacyPickaxeTool());

        config.setHost("127.0.0.1");
        Assertions.assertEquals("127.0.0.1", config.getHost());

        config.setPort(9000);
        Assertions.assertEquals(9000, config.getPort());

        // Invalid port check (below 1024 or above 65535 should be ignored)
        config.setPort(80);
        Assertions.assertEquals(9000, config.getPort());

        config.setPort(70000);
        Assertions.assertEquals(9000, config.getPort());

        config.setAutoStartOnWorldLoad(true);
        Assertions.assertTrue(config.isAutoStartOnWorldLoad());

        config.setEnableLegacyPickaxeTool(true);
        Assertions.assertTrue(config.isEnableLegacyPickaxeTool());
    }
}
