package tn.esprit.userservice.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;
import tn.esprit.userservice.entity.RoleEnum;
import tn.esprit.userservice.entity.UserStatus;

@Data
public class UserRequest {

    @NotBlank(message = "Full name is required")
    private String fullName;

    @NotBlank(message = "Email is required")
    @Email(message = "Email is invalid")
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    private String password;

    // Rendre le rôle OBLIGATOIRE - plus de valeur par défaut
    @NotNull(message = "Role is required")
    private RoleEnum role;

    private UserStatus status;
}