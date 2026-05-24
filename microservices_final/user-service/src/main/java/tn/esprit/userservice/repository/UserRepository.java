package tn.esprit.userservice.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;
import tn.esprit.userservice.entity.User;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmail(String email);

    // ⚠️ SUPPRIMER ces méthodes si elles existent :
    // Optional<User> findByUsername(String username);
    // boolean existsByUsername(String username);

    Optional<User> findByVerificationToken(String token);
    Optional<User> findByResetToken(String token);

    boolean existsByEmail(String email);

    @Modifying
    @Transactional
    @Query("UPDATE User u SET u.emailVerified = true, u.status = 'ACTIVE', u.verificationToken = null, u.verificationTokenExpiry = null WHERE u.verificationToken = :token")
    int verifyEmail(@Param("token") String token);

    @Modifying
    @Transactional
    @Query("UPDATE User u SET u.lastLogin = :lastLogin WHERE u.id = :userId")
    void updateLastLogin(@Param("userId") Long userId, @Param("lastLogin") LocalDateTime lastLogin);
}