function showLoginAlert() {
   
    window.location.href = "/login?alert=1";

}

    document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    if(params.get("alert") === "1") {
        const alertBox = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>Login required!</strong> Please log in to access.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;

        document.getElementById('login-alert-container').innerHTML = alertBox;

        setTimeout(() => {
            document.getElementById('login-alert-container').innerHTML = '';
        
        }, 5000);
        
    }
});

  