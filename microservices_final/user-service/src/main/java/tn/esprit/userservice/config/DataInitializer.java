package tn.esprit.userservice.config;

import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import tn.esprit.userservice.entity.RoleEnum;
import tn.esprit.userservice.entity.User;
import tn.esprit.userservice.entity.UserStatus;
import tn.esprit.userservice.repository.UserRepository;

import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) throws Exception {
        if (userRepository.count() == 0) {
            initializeUsers();
        }
    }

    private void initializeUsers() {
        // Admin
        User admin = new User();
        admin.setFullName("System Administrator");
        admin.setEmail("admin@test.com");
        admin.setPassword(passwordEncoder.encode("admin123"));
        admin.setRole(RoleEnum.SYSTEM_ADMIN);
        admin.setStatus(UserStatus.ACTIVE);
        admin.setEmailVerified(true);
        admin.setCreatedAt(LocalDateTime.now());
        admin.setUpdatedAt(LocalDateTime.now());
        userRepository.save(admin);

        // Data Scientist
        User dataScientist = new User();
        dataScientist.setFullName("Data Scientist Test");
        dataScientist.setEmail("ds@test.com");
        dataScientist.setPassword(passwordEncoder.encode("ds123"));
        dataScientist.setRole(RoleEnum.DATA_SCIENTIST);
        dataScientist.setStatus(UserStatus.ACTIVE);
        dataScientist.setEmailVerified(true);
        dataScientist.setCreatedAt(LocalDateTime.now());
        dataScientist.setUpdatedAt(LocalDateTime.now());
        userRepository.save(dataScientist);

        // RAN Engineer
        User ranEngineer = new User();
        ranEngineer.setFullName("RAN Engineer Test");
        ranEngineer.setEmail("ran@test.com");
        ranEngineer.setPassword(passwordEncoder.encode("ran123"));
        ranEngineer.setRole(RoleEnum.RAN_ENGINEER);
        ranEngineer.setStatus(UserStatus.ACTIVE);
        ranEngineer.setEmailVerified(true);
        ranEngineer.setCreatedAt(LocalDateTime.now());
        ranEngineer.setUpdatedAt(LocalDateTime.now());
        userRepository.save(ranEngineer);

        // NOC Engineer
        User nocEngineer = new User();
        nocEngineer.setFullName("NOC Engineer Test");
        nocEngineer.setEmail("noc@test.com");
        nocEngineer.setPassword(passwordEncoder.encode("noc123"));
        nocEngineer.setRole(RoleEnum.NOC_ENGINEER);
        nocEngineer.setStatus(UserStatus.ACTIVE);
        nocEngineer.setEmailVerified(true);
        nocEngineer.setCreatedAt(LocalDateTime.now());
        nocEngineer.setUpdatedAt(LocalDateTime.now());
        userRepository.save(nocEngineer);

        // Core Engineer (anciennement Performance Engineer)
        User coreEngineer = new User();
        coreEngineer.setFullName("Core Engineer Test");
        coreEngineer.setEmail("core@test.com");
        coreEngineer.setPassword(passwordEncoder.encode("core123"));
        coreEngineer.setRole(RoleEnum.CORE_ENGINEER);
        coreEngineer.setStatus(UserStatus.ACTIVE);
        coreEngineer.setEmailVerified(true);
        coreEngineer.setCreatedAt(LocalDateTime.now());
        coreEngineer.setUpdatedAt(LocalDateTime.now());
        userRepository.save(coreEngineer);

        System.out.println("=== UTILISATEURS DE TEST CRÉÉS ===");
        System.out.println("Admin: admin@test.com / admin123");
        System.out.println("Data Scientist: ds@test.com / ds123");
        System.out.println("RAN Engineer: ran@test.com / ran123");
        System.out.println("NOC Engineer: noc@test.com / noc123");
        System.out.println("Core Engineer: core@test.com / core123");
        System.out.println("================================");
    }
}