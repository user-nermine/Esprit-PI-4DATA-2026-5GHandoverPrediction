package tn.esprit.ms_reporting;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class MsReportingApplicationTests {

    @MockBean
    private JavaMailSender javaMailSender;

    @Test
    void contextLoads() {
    }
}