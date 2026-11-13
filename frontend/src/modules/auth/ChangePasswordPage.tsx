import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../api/client.ts";
import { removeToken } from "../../api/token.ts";
import { Alert } from "../../components/ui/Alert.tsx";
import { Button } from "../../components/ui/Button.tsx";
import { Input } from "../../components/ui/Input.tsx";
import { useAuth } from "./AuthContext.tsx";
import { can } from "../../lib/permissions.ts";

export function ChangePasswordPage() {
    const { logout, user } = useAuth();
    const navigate = useNavigate();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        if (user && !user.must_change_password) {
            navigate(
                can(user, "dashboard.read")
                    ? "/admin/dashboard"
                    : can(user, "station.use")
                      ? "/station/scan"
                      : "/profile",
                { replace: true },
            );
        }
    }, [user, navigate]);

    async function submit(event: React.FormEvent) {
        event.preventDefault();
        setBusy(true);
        setError("");
        try {
            await apiClient.post("/api/v1/auth/change-password", {
                current_password: currentPassword,
                new_password: newPassword,
            });
            removeToken();
            logout();
            navigate("/login", { replace: true });
        } catch (reason) {
            setError(
                reason instanceof Error
                    ? reason.message
                    : "Không thể đổi mật khẩu.",
            );
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="auth-page">
            <section
                className="auth-card"
                style={{ maxWidth: 520, padding: 32 }}
                aria-labelledby="change-password-heading"
            >
                <header className="auth-panel-heading">
                    <p className="auth-panel-kicker">BẢO MẬT TÀI KHOẢN</p>
                    <h1 id="change-password-heading">Đổi mật khẩu</h1>
                    <p>
                        Đây là mật khẩu tạm thời. Bạn cần đổi mật khẩu trước khi
                        sử dụng hệ thống.
                    </p>
                </header>
                {error ? <Alert variant="error">{error}</Alert> : null}
                <form onSubmit={submit} className="stack">
                    <Input
                        label="Mật khẩu hiện tại"
                        name="current-password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={currentPassword}
                        disabled={busy}
                        onChange={(event) =>
                            setCurrentPassword(event.target.value)
                        }
                    />
                    <Input
                        label="Mật khẩu mới"
                        name="new-password"
                        type="password"
                        autoComplete="new-password"
                        minLength={8}
                        required
                        value={newPassword}
                        disabled={busy}
                        onChange={(event) => setNewPassword(event.target.value)}
                    />
                    <Button type="submit" loading={busy}>
                        Đổi mật khẩu
                    </Button>
                </form>
            </section>
        </div>
    );
}
