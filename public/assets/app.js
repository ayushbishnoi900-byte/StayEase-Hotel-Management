// ======================================
// STAYEASE - FRONTEND JAVASCRIPT
// Complete Customer Booking Experience
// ======================================

// Backend API URL (empty string for same origin)
const API = "";

// Store logged-in customer in memory & localStorage
let currentUser = JSON.parse(
    localStorage.getItem("customer") || "null"
);

// Current authentication mode: "login" or "register"
let authMode = "login";

// Stored pending booking state for continuing after login
let pendingBookingState = null;

// Cache of loaded rooms & user bookings
let currentRoomsCache = [];
let allUserBookings = [];
let activeBookingFilter = "all";

// Active booking being reviewed or confirmed
let activeBookingContext = null;
let lastConfirmedBookingId = null;


// ======================================
// 1. TOAST NOTIFICATION SYSTEM
// ======================================

function showToast(message, type) {
    if (!type) type = "success";

    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(function () {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(function () {
            toast.remove();
        }, 300);
    }, 4000);
}


// ======================================
// 2. AUTHENTICATED API HELPER
// ======================================

async function authFetch(url, options) {
    if (!options) options = {};

    const token = localStorage.getItem("access_token");

    if (!options.headers) {
        options.headers = {};
    }

    if (token) {
        options.headers["Authorization"] = "Bearer " + token;
    }

    if (options.body && !options.headers["Content-Type"]) {
        options.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(API + url, options);

    if (response.status === 401 || response.status === 403) {
        localStorage.removeItem("customer");
        localStorage.removeItem("access_token");
        currentUser = null;
        updateNavbar();

        if (url !== "/login" && url !== "/register") {
            showToast("Session expired. Please log in again.", "error");
            openAuth("login");
            throw new Error("Authentication required");
        }
    }

    return response;
}


// ======================================
// 3. AUTHENTICATION (STEP 4)
// ======================================

function openAuth(mode, customNotice) {
    authMode = mode;
    document.getElementById("authModal").style.display = "flex";

    const noticeEl = document.getElementById("authNotice");
    if (customNotice) {
        noticeEl.textContent = customNotice;
        noticeEl.classList.remove("hidden");
    } else {
        noticeEl.classList.add("hidden");
    }

    const errorAlert = document.getElementById("authErrorAlert");
    if (errorAlert) {
        errorAlert.classList.add("hidden");
        errorAlert.textContent = "";
    }

    updateAuthForm();
}

function closeAuth() {
    document.getElementById("authModal").style.display = "none";
    document.getElementById("passwordStrength").classList.add("hidden");
    document.getElementById("authNotice").classList.add("hidden");
    const errorAlert = document.getElementById("authErrorAlert");
    if (errorAlert) errorAlert.classList.add("hidden");
    document.getElementById("authForm").reset();
}

function switchAuth(event) {
    if (event) event.preventDefault();
    authMode = authMode === "login" ? "register" : "login";
    updateAuthForm();
    const errorAlert = document.getElementById("authErrorAlert");
    if (errorAlert) errorAlert.classList.add("hidden");
}

function updateAuthForm() {
    const isRegister = authMode === "register";

    document.getElementById("authTitle").textContent =
        isRegister ? "Create Guest Account" : "Welcome Back";

    document.getElementById("authDescription").textContent =
        isRegister
            ? "Register to begin reserving suites and tracking your bookings."
            : "Sign in with your email and password to access your account.";

    document.getElementById("nameField").classList.toggle("hidden", !isRegister);
    document.getElementById("phoneField").classList.toggle("hidden", !isRegister);
    document.getElementById("name").required = isRegister;
    document.getElementById("passwordStrength").classList.toggle("hidden", !isRegister);

    const submitBtn = document.getElementById("authSubmitBtn");
    submitBtn.innerHTML = isRegister ? "Create Account →" : "Sign In →";

    document.getElementById("switchText").innerHTML =
        isRegister
            ? 'Already have an account? <a href="#" onclick="switchAuth(event)">Sign In</a>'
            : 'Don\'t have an account? <a href="#" onclick="switchAuth(event)">Register for free</a>';
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "🙈";
        btn.title = "Hide password";
    } else {
        input.type = "password";
        btn.textContent = "👁️";
        btn.title = "Show password";
    }
}

document.getElementById("authForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const submitBtn = document.getElementById("authSubmitBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-spinner"></span> Authenticating...';

    const errorAlert = document.getElementById("authErrorAlert");
    if (errorAlert) errorAlert.classList.add("hidden");

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    let endpoint;
    let data;

    if (authMode === "register") {
        endpoint = "/register";
        data = {
            name: document.getElementById("name").value.trim(),
            email: email,
            password: password,
            phone: document.getElementById("phone").value.trim()
        };
    } else {
        endpoint = "/login";
        data = {
            email: email,
            password: password
        };
    }

    try {
        const response = await fetch(API + endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Authentication failed. Please check credentials.");
        }

        if (authMode === "register") {
            showToast("Registration successful! Please sign in with your password.");
            authMode = "login";
            updateAuthForm();
            document.getElementById("authForm").reset();
        } else {
            currentUser = result.customer;
            localStorage.setItem("customer", JSON.stringify(currentUser));
            localStorage.setItem("access_token", result.access_token);

            showToast("Welcome back, " + currentUser.name + "!");
            closeAuth();
            updateNavbar();

            // Resume pending booking if customer was in the middle of booking
            if (pendingBookingState) {
                const pending = pendingBookingState;
                pendingBookingState = null;
                openBookingConfirm(pending);
            }
        }
    } catch (error) {
        if (errorAlert) {
            errorAlert.textContent = "⚠️ " + error.message;
            errorAlert.classList.remove("hidden");
        }
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = authMode === "register" ? "Create Account →" : "Sign In →";
    }
});


// ======================================
// 4. NAVBAR & USER SESSION
// ======================================

function getInitials(name) {
    if (!name) return "G";
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function toggleProfileDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById("profileDropdownMenu");
    if (menu) menu.classList.toggle("active");
}

document.addEventListener("click", function (event) {
    const wrapper = document.getElementById("profileDropdownWrapper");
    if (wrapper && !wrapper.contains(event.target)) {
        const menu = document.getElementById("profileDropdownMenu");
        if (menu) menu.classList.remove("active");
    }
});

function updateNavbar() {
    const nav = document.getElementById("navButtons");
    const myBookingsLink = document.getElementById("myBookingsLink");
    const adminLink = document.getElementById("adminLink");

    if (currentUser) {
        if (myBookingsLink) myBookingsLink.classList.remove("hidden");

        if (currentUser.role === "admin") {
            if (adminLink) adminLink.classList.remove("hidden");
        } else {
            if (adminLink) adminLink.classList.add("hidden");
        }

        const initials = getInitials(currentUser.name);
        const roleLabel = currentUser.role === "admin" ? "Administrator" : "Verified Guest";
        const roleClass = currentUser.role === "admin" ? "role-badge-admin" : "role-badge-cust";

        nav.innerHTML =
            '<div class="profile-dropdown-wrapper" id="profileDropdownWrapper">' +
                '<button class="profile-dropdown-trigger" onclick="toggleProfileDropdown(event)" aria-label="Customer Account Menu">' +
                    '<span class="profile-avatar-circle">' + initials + '</span>' +
                    '<span class="profile-trigger-name">' + escapeHTML(currentUser.name) + '</span>' +
                    '<span class="profile-trigger-arrow">▾</span>' +
                '</button>' +
                '<div class="profile-dropdown-menu" id="profileDropdownMenu">' +
                    '<div class="dropdown-header">' +
                        '<strong>' + escapeHTML(currentUser.name) + '</strong>' +
                        '<small>' + escapeHTML(currentUser.email) + '</small>' +
                        '<span class="role-badge ' + roleClass + '">' + roleLabel + '</span>' +
                    '</div>' +
                    '<div class="dropdown-divider"></div>' +
                    '<button class="dropdown-item" onclick="openProfileModal(); toggleProfileDropdown();"><span class="dropdown-icon">👤</span> My Profile</button>' +
                    '<button class="dropdown-item" onclick="showSection(\'my-bookings\'); toggleProfileDropdown();"><span class="dropdown-icon">📋</span> My Bookings</button>' +
                    (currentUser.role === "admin" ? '<button class="dropdown-item" onclick="showSection(\'admin\'); toggleProfileDropdown();"><span class="dropdown-icon">⚙️</span> Admin Portal</button>' : '') +
                    '<div class="dropdown-divider"></div>' +
                    '<button class="dropdown-item dropdown-logout-btn" onclick="logout();"><span class="dropdown-icon">🚪</span> Sign Out</button>' +
                '</div>' +
            '</div>';
    } else {
        if (myBookingsLink) myBookingsLink.classList.add("hidden");
        if (adminLink) adminLink.classList.add("hidden");

        nav.innerHTML =
            '<button class="login-btn" onclick="openAuth(\'login\')">Sign In</button>' +
            '<button class="signup-btn" onclick="openAuth(\'register\')">Book a Room</button>';
    }
}

function logout() {
    localStorage.removeItem("customer");
    localStorage.removeItem("access_token");
    currentUser = null;
    pendingBookingState = null;
    updateNavbar();
    showSection("home");
    showToast("You have been signed out successfully.");
}


// ======================================
// 5. STEP 1: BROWSE ROOMS
// ======================================

async function loadRooms(queryParams = "") {
    const container = document.getElementById("roomsContainer");
    container.innerHTML = '<p class="empty-state">Loading available rooms...</p>';

    try {
        const url = API + "/rooms" + (queryParams ? "?" + queryParams : "");
        const response = await fetch(url);
        if (!response.ok) {
            let errorMsg = "Unable to load rooms";
            try {
                const rawText = await response.text();
                try {
                    const err = JSON.parse(rawText);
                    errorMsg = err.detail || errorMsg;
                } catch (_) {
                    if (rawText && rawText.length < 200) {
                        errorMsg = rawText;
                    }
                }
            } catch (_) {}
            throw new Error(errorMsg);
        }

        const rooms = await response.json();
        currentRoomsCache = rooms;

        if (rooms.length === 0) {
            container.innerHTML =
                '<div class="empty-state">' +
                '<p>No rooms match your search criteria.</p>' +
                '<button class="primary-btn small" onclick="resetSearch()">View All Rooms</button>' +
                '</div>';
            return;
        }

        container.innerHTML = rooms.map(function (room) {
            let image = room.image_url;
            if (!image) {
                if (room.room_type === "Suite") {
                    image = "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=700";
                } else if (room.room_type === "Deluxe") {
                    image = "https://images.unsplash.com/photo-1590490360182-c33d955571d7?w=700";
                } else {
                    image = "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=700";
                }
            }

            const amenities = (room.amenities || []).slice(0, 3).map(function (a) {
                return '<span class="amenity-tag">✓ ' + escapeHTML(a) + '</span>';
            }).join("");

            return '<div class="room-card">' +
                '<div class="room-card-media">' +
                '<img class="room-image" src="' + image + '" alt="' + escapeHTML(room.room_type) + ' Room">' +
                '<span class="room-category-pill">' + escapeHTML(room.room_type) + '</span>' +
                '</div>' +

                '<div class="room-info">' +
                '<div class="room-header-meta">' +
                '<h3>' + escapeHTML(room.room_type) + ' Room</h3>' +
                '<span class="room-number-badge">Room ' + escapeHTML(room.room_number) + '</span>' +
                '</div>' +

                '<p class="room-capacity-text">👥 Up to ' + room.capacity + ' Guest' + (room.capacity > 1 ? 's' : '') + '</p>' +

                '<p class="room-desc">' + escapeHTML(room.description || "Comfortable and elegant room equipped with modern amenities.") + '</p>' +

                '<div class="room-amenities-preview">' + amenities + '</div>' +

                '<div class="room-price-row">' +
                '<p class="room-price">₹' + Number(room.price).toLocaleString("en-IN") + ' <small>/ night</small></p>' +
                '</div>' +

                '<div class="room-card-actions">' +
                '<button class="secondary-btn small" onclick="openRoomDetails(' + room.id + ')">View Details</button>' +
                '<button class="primary-btn small" onclick="startBookingFlow(' + room.id + ')">Book Now</button>' +
                '</div>' +

                '</div>' +
                '</div>';
        }).join("");
    } catch (error) {
        container.innerHTML = '<p class="empty-state error-text">⚠️ ' + escapeHTML(error.message) + '</p>';
        console.error(error);
    }
}


// ======================================
// 6. STEP 2: SEARCH & FILTER ROOMS
// ======================================

function searchRooms() {
    const searchBtn = document.getElementById("searchRoomsBtn");
    const checkIn = document.getElementById("checkIn").value;
    const checkOut = document.getElementById("checkOut").value;
    const roomType = document.getElementById("roomFilter").value;
    const guests = document.getElementById("guestFilter").value;
    const minPrice = document.getElementById("minPriceFilter").value;
    const maxPrice = document.getElementById("maxPriceFilter").value;

    const today = new Date().toISOString().split("T")[0];

    // Validate dates if either is provided
    if (checkIn && checkIn < today) {
        showToast("Check-in date cannot be in the past.", "error");
        return;
    }

    if (checkIn && checkOut && checkOut <= checkIn) {
        showToast("Check-out date must be after check-in date.", "error");
        return;
    }

    if ((checkIn && !checkOut) || (!checkIn && checkOut)) {
        showToast("Please specify both check-in and check-out dates for live availability.", "error");
        return;
    }

    const params = new URLSearchParams();
    if (roomType) params.append("room_type", roomType);
    if (guests) params.append("capacity", guests);
    if (minPrice) params.append("min_price", minPrice);
    if (maxPrice) params.append("max_price", maxPrice);
    if (checkIn && checkOut) {
        params.append("check_in", checkIn);
        params.append("check_out", checkOut);
    }

    searchBtn.textContent = "Searching...";
    searchBtn.disabled = true;

    loadRooms(params.toString()).finally(function () {
        searchBtn.textContent = "🔍 Search";
        searchBtn.disabled = false;
        document.getElementById("rooms").scrollIntoView({ behavior: "smooth" });
    });
}

function resetSearch() {
    document.getElementById("checkIn").value = "";
    document.getElementById("checkOut").value = "";
    document.getElementById("roomFilter").value = "";
    document.getElementById("guestFilter").value = "";
    document.getElementById("minPriceFilter").value = "";
    document.getElementById("maxPriceFilter").value = "";

    loadRooms();
}


// ======================================
// 7. STEP 3: ROOM DETAILS MODAL
// ======================================

async function openRoomDetails(roomId) {
    try {
        const response = await fetch(API + "/rooms/" + roomId);
        if (!response.ok) throw new Error("Could not load room details");
        const room = await response.json();

        activeBookingContext = {
            room: room,
            roomId: room.id,
            price: room.price
        };

        // Populate media & text
        document.getElementById("detailRoomImage").src = room.image_url || "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=700";
        document.getElementById("detailRoomBadge").textContent = room.room_type;
        document.getElementById("detailRoomTitle").textContent = room.room_type + " Room";
        document.getElementById("detailRoomNumber").textContent = "Room Number: " + room.room_number + " • Up to " + room.capacity + " Guests";
        document.getElementById("detailRoomDescription").textContent = room.description || "Indulge in a tranquil retreat featuring plush bedding, modern conveniences, and warm hospitality.";

        // Populate amenities pills
        const amenitiesContainer = document.getElementById("detailRoomAmenities");
        amenitiesContainer.innerHTML = (room.amenities || []).map(function (a) {
            return '<div class="amenity-pill"><span>✓</span> ' + escapeHTML(a) + '</div>';
        }).join("");

        // Populate dates
        const today = new Date().toISOString().split("T")[0];
        const checkInInput = document.getElementById("detailCheckIn");
        const checkOutInput = document.getElementById("detailCheckOut");
        checkInInput.min = today;

        // Carry over search dates if available
        const searchIn = document.getElementById("checkIn").value;
        const searchOut = document.getElementById("checkOut").value;

        checkInInput.value = (searchIn && searchIn >= today) ? searchIn : "";
        checkOutInput.value = (searchOut && searchOut > checkInInput.value) ? searchOut : "";

        // Populate guests dropdown
        const guestsSelect = document.getElementById("detailGuests");
        guestsSelect.innerHTML = "";
        for (let i = 1; i <= room.capacity; i++) {
            const opt = document.createElement("option");
            opt.value = i;
            opt.textContent = i + " Guest" + (i > 1 ? "s" : "");
            guestsSelect.appendChild(opt);
        }

        document.getElementById("detailNightlyRate").textContent = "₹" + Number(room.price).toLocaleString("en-IN") + " / night";
        updateDetailPrice();

        document.getElementById("roomDetailsModal").style.display = "flex";
    } catch (e) {
        showToast(e.message, "error");
    }
}

function closeRoomDetails() {
    document.getElementById("roomDetailsModal").style.display = "none";
}

function updateDetailPrice() {
    if (!activeBookingContext) return;

    const checkIn = document.getElementById("detailCheckIn").value;
    const checkOut = document.getElementById("detailCheckOut").value;
    const totalEl = document.getElementById("detailEstimatedTotal");
    const checkOutInput = document.getElementById("detailCheckOut");

    if (checkIn) {
        const nextDay = new Date(checkIn);
        nextDay.setDate(nextDay.getDate() + 1);
        checkOutInput.min = nextDay.toISOString().split("T")[0];
    }

    if (checkIn && checkOut) {
        const nights = Math.ceil((new Date(checkOut) - new Date(checkIn)) / (1000 * 60 * 60 * 24));
        if (nights > 0) {
            const total = nights * activeBookingContext.price;
            totalEl.textContent = "₹" + Number(total).toLocaleString("en-IN") + " (" + nights + " night" + (nights > 1 ? "s" : "") + ")";
        } else {
            totalEl.textContent = "Check-out must be after check-in";
        }
    } else {
        totalEl.textContent = "Select dates";
    }
}


// ======================================
// 8. STEP 4 & 5: BOOKING FLOW & CONFIRMATION
// ======================================

function startBookingFlow(roomId) {
    // Open details modal first to select dates and guests accurately
    openRoomDetails(roomId);
}

function proceedToBookingReview() {
    if (!activeBookingContext) return;

    const checkIn = document.getElementById("detailCheckIn").value;
    const checkOut = document.getElementById("detailCheckOut").value;
    const guests = Number(document.getElementById("detailGuests").value || 1);

    const today = new Date().toISOString().split("T")[0];
    if (!checkIn || checkIn < today) {
        showToast("Please choose a valid check-in date.", "error");
        return;
    }
    if (!checkOut || checkOut <= checkIn) {
        showToast("Check-out date must be after check-in date.", "error");
        return;
    }

    const nights = Math.ceil((new Date(checkOut) - new Date(checkIn)) / (1000 * 60 * 60 * 24));
    const totalPrice = nights * activeBookingContext.price;

    const bookingData = {
        roomId: activeBookingContext.roomId,
        room: activeBookingContext.room,
        checkIn: checkIn,
        checkOut: checkOut,
        nights: nights,
        guests: guests,
        totalPrice: totalPrice
    };

    // STEP 4: Authentication Gate
    if (!currentUser) {
        pendingBookingState = bookingData;
        closeRoomDetails();
        openAuth("login", "Please login or register to complete your reservation.");
        return;
    }

    closeRoomDetails();
    openBookingConfirm(bookingData);
}

function openBookingConfirm(bookingData) {
    activeBookingContext = bookingData;

    document.getElementById("reviewCustomerName").textContent = currentUser.name + " (" + currentUser.email + ")";
    document.getElementById("reviewRoomName").textContent =
        bookingData.room.room_type + " Room (Room #" + bookingData.room.room_number + ")";
    document.getElementById("reviewDates").textContent = bookingData.checkIn + " → " + bookingData.checkOut;
    document.getElementById("reviewNights").textContent = bookingData.nights + " Night" + (bookingData.nights > 1 ? "s" : "");
    document.getElementById("reviewGuests").textContent = bookingData.guests + " Guest" + (bookingData.guests > 1 ? "s" : "");
    document.getElementById("reviewNightlyPrice").textContent = "₹" + Number(bookingData.room.price).toLocaleString("en-IN");
    document.getElementById("reviewTotalPrice").textContent = "₹" + Number(bookingData.totalPrice).toLocaleString("en-IN");

    document.getElementById("bookingConfirmModal").style.display = "flex";
}

function closeBookingConfirm() {
    document.getElementById("bookingConfirmModal").style.display = "none";
}

function backToRoomDetails() {
    closeBookingConfirm();
    if (activeBookingContext && activeBookingContext.roomId) {
        openRoomDetails(activeBookingContext.roomId);
    }
}


// ======================================
// 9. STEP 6: BOOKING SUBMISSION & SUCCESS
// ======================================

async function submitFinalBooking() {
    if (!activeBookingContext || !currentUser) return;

    const submitBtn = document.getElementById("finalConfirmBookingBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Verifying & Confirming...";

    const paymentMethod = document.getElementById("confirmPaymentMethod").value;

    try {
        const response = await authFetch("/bookings", {
            method: "POST",
            body: JSON.stringify({
                room_id: activeBookingContext.roomId,
                check_in: activeBookingContext.checkIn,
                check_out: activeBookingContext.checkOut,
                guests: activeBookingContext.guests,
                payment_method: paymentMethod
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Booking failed");
        }

        const booking = result.booking;
        lastConfirmedBookingId = booking.id;

        closeBookingConfirm();

        // STEP 6: Open Booking Success Screen
        document.getElementById("successBookingRef").textContent = booking.booking_reference || ("SE-BK-" + booking.id);

        document.getElementById("successSummaryContent").innerHTML =
            '<div class="success-row"><span>Room:</span><strong>' + escapeHTML(booking.room_type) + ' (#' + escapeHTML(booking.room_number) + ')</strong></div>' +
            '<div class="success-row"><span>Dates:</span><strong>' + booking.check_in + ' → ' + booking.check_out + ' (' + booking.nights + ' nights)</strong></div>' +
            '<div class="success-row"><span>Guests:</span><strong>' + booking.guests + '</strong></div>' +
            '<div class="success-row"><span>Total Amount:</span><strong>₹' + Number(booking.total_price).toLocaleString("en-IN") + '</strong></div>' +
            '<div class="success-row"><span>Payment:</span><strong>' + escapeHTML(booking.payment.status) + ' (' + escapeHTML(booking.payment.method) + ')</strong></div>';

        document.getElementById("bookingSuccessModal").style.display = "flex";

        // Refresh live room availability in background
        loadRooms();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Confirm Reservation";
    }
}

function openInvoiceFromSuccess() {
    document.getElementById("bookingSuccessModal").style.display = "none";
    if (lastConfirmedBookingId) {
        openInvoice(lastConfirmedBookingId);
    }
}

function viewBookingsFromSuccess() {
    document.getElementById("bookingSuccessModal").style.display = "none";
    showSection("my-bookings");
}


// ======================================
// 10. STEP 7: MY BOOKINGS (TABS & ACTIONS)
// ======================================

async function loadMyBookings() {
    const container = document.getElementById("bookingsList");
    container.innerHTML = '<p class="empty-state">Loading your reservations...</p>';

    try {
        const response = await authFetch("/my-bookings");
        if (!response.ok) throw new Error("Failed to load bookings");

        allUserBookings = await response.json();
        renderMyBookings();
    } catch (error) {
        if (error.message !== "Authentication required") {
            container.innerHTML = '<p class="empty-state error-text">Unable to load bookings.</p>';
        }
        console.error(error);
    }
}

function filterMyBookings(filterType, btn) {
    activeBookingFilter = filterType;

    document.querySelectorAll(".booking-tab-btn").forEach(function (b) {
        b.classList.remove("active");
    });
    if (btn) btn.classList.add("active");

    renderMyBookings();
}

function renderMyBookings() {
    const container = document.getElementById("bookingsList");

    let filtered = allUserBookings;
    if (activeBookingFilter !== "all") {
        filtered = allUserBookings.filter(function (b) {
            return (b.timing_status || "").toLowerCase() === activeBookingFilter;
        });
    }

    if (filtered.length === 0) {
        container.innerHTML =
            '<div class="empty-state">' +
            '<p>No ' + (activeBookingFilter === "all" ? "" : activeBookingFilter + " ") + 'reservations found.</p>' +
            '<button class="primary-btn small" onclick="showSection(\'rooms\')">Explore Rooms</button>' +
            '</div>';
        return;
    }

    container.innerHTML = filtered.map(function (b) {
        const timing = b.timing_status || "Upcoming";
        let timingBadgeClass = "timing-upcoming";
        if (timing === "Completed") timingBadgeClass = "timing-completed";
        if (timing === "Cancelled") timingBadgeClass = "timing-cancelled";

        const pStatusClass = b.payment_status === "Completed" ? "status-confirmed" : "status-cancelled";

        let payButton = "";
        if (b.status === "Confirmed" && b.payment_status !== "Completed") {
            payButton = '<button class="action-btn pay-btn" onclick="openDemoPay(' + b.id + ', ' + b.total_price + ')">💳 Pay (Demo)</button>';
        }

        let cancelButton = "";
        if (b.can_cancel) {
            cancelButton = '<button class="cancel-btn" onclick="cancelBooking(' + b.id + ')">Cancel Reservation</button>';
        }

        const invoiceButton = '<button class="action-btn invoice-btn" onclick="openInvoice(' + b.id + ')">🧾 Invoice</button>';

        return '<div class="booking-card">' +
            '<div class="booking-info">' +
            '<div class="booking-card-head">' +
            '<h3>' + escapeHTML(b.room_type) + ' Room</h3>' +
            '<span class="booking-ref-badge">' + escapeHTML(b.booking_reference || ("#" + b.id)) + '</span>' +
            '<span class="timing-badge ' + timingBadgeClass + '">' + timing + '</span>' +
            '</div>' +

            '<p class="booking-dates-line">📅 ' + b.check_in + ' → ' + b.check_out + ' (' + b.nights + ' night' + (b.nights > 1 ? 's' : '') + ')</p>' +
            '<p>Room ' + escapeHTML(b.room_number) + ' • ' + b.guests + ' Guest' + (b.guests > 1 ? 's' : '') + '</p>' +
            '<p>Payment: <span class="status-badge ' + pStatusClass + '">' + escapeHTML(b.payment_status) + '</span> (' + escapeHTML(b.payment_method) + ')' +
            (b.transaction_ref ? ' • <code>' + escapeHTML(b.transaction_ref) + '</code>' : '') +
            '</p>' +
            '</div>' +

            '<div class="booking-actions">' +
            '<p class="booking-price">₹' + Number(b.total_price).toLocaleString("en-IN") + '</p>' +
            '<div class="booking-button-group">' +
            invoiceButton +
            payButton +
            cancelButton +
            '</div>' +
            '</div>' +
            '</div>';
    }).join("");
}

async function cancelBooking(bookingId) {
    if (!confirm("Are you sure you want to cancel booking #" + bookingId + "? This will release your reserved dates.")) return;

    try {
        const response = await authFetch("/bookings/cancel/" + bookingId, {
            method: "PUT"
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Cancellation failed");

        showToast("Reservation cancelled successfully.");
        loadMyBookings();
        loadRooms(); // Refresh room catalog availability
    } catch (error) {
        showToast(error.message, "error");
    }
}


// ======================================
// 11. STEP 8: BILLING & PRINTABLE INVOICE
// ======================================

async function openInvoice(bookingId) {
    try {
        const response = await authFetch("/bookings/" + bookingId + "/invoice");
        if (!response.ok) throw new Error("Could not generate invoice");
        const inv = await response.json();

        document.getElementById("invNumber").textContent = inv.invoice_number;
        document.getElementById("invRef").textContent = inv.booking_reference;
        document.getElementById("invDate").textContent = inv.issue_date;
        document.getElementById("invPaymentStatus").textContent = inv.billing.payment_status;

        const pStatusEl = document.getElementById("invPaymentStatus");
        pStatusEl.className = "status-badge " + (inv.billing.payment_status === "Completed" ? "status-confirmed" : "status-cancelled");

        document.getElementById("invCustName").textContent = inv.customer.name;
        document.getElementById("invCustEmail").textContent = inv.customer.email;
        document.getElementById("invCustPhone").textContent = inv.customer.phone || "-";

        document.getElementById("invRoom").textContent = "Room " + inv.reservation.room_number + " (" + inv.reservation.room_type + ")";
        document.getElementById("invCheckIn").textContent = inv.reservation.check_in;
        document.getElementById("invCheckOut").textContent = inv.reservation.check_out;
        document.getElementById("invGuests").textContent = inv.reservation.guests;

        document.getElementById("invItemDesc").textContent = inv.reservation.room_type + " Room Accommodation";
        document.getElementById("invItemRate").textContent = "₹" + Number(inv.reservation.price_per_night).toLocaleString("en-IN");
        document.getElementById("invItemNights").textContent = inv.reservation.nights + " Night" + (inv.reservation.nights > 1 ? "s" : "");
        document.getElementById("invItemAmount").textContent = "₹" + Number(inv.billing.subtotal).toLocaleString("en-IN");

        document.getElementById("invSubtotal").textContent = "₹" + Number(inv.billing.subtotal).toLocaleString("en-IN");
        document.getElementById("invGrandTotal").textContent = "₹" + Number(inv.billing.total_amount).toLocaleString("en-IN");

        document.getElementById("invPayMethod").textContent = inv.billing.payment_method;
        document.getElementById("invTxRef").textContent = inv.billing.transaction_reference || "N/A";

        document.getElementById("invoiceModal").style.display = "flex";
    } catch (e) {
        showToast(e.message, "error");
    }
}

function closeInvoice() {
    document.getElementById("invoiceModal").style.display = "none";
}

function printInvoice() {
    window.print();
}


// ======================================
// 12. DEMONSTRATION PAYMENT MODAL
// ======================================

function openDemoPay(bookingId, amount) {
    document.getElementById("demoPayBookingId").value = bookingId;
    document.getElementById("demoPayDescription").textContent =
        "Complete payment of ₹" + Number(amount).toLocaleString("en-IN") + " for Booking #" + bookingId;
    document.getElementById("demoPayModal").style.display = "flex";
}

function closeDemoPay() {
    document.getElementById("demoPayModal").style.display = "none";
}

document.getElementById("demoPayForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const submitBtn = document.getElementById("demoPaySubmitBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Simulating...";

    const bookingId = document.getElementById("demoPayBookingId").value;
    const method = document.getElementById("demoPayMethod").value;

    try {
        const response = await authFetch("/bookings/" + bookingId + "/pay", {
            method: "POST",
            body: JSON.stringify({
                payment_method: method,
                card_last4: "4242"
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Payment failed");

        showToast("Demo Payment Recorded! Tx: " + result.payment.transaction_ref);
        closeDemoPay();
        loadMyBookings();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Process Demo Payment";
    }
});


// ======================================
// 13. CUSTOMER PROFILE MODAL
// ======================================

async function openProfileModal() {
    if (!currentUser) return;

    try {
        const response = await authFetch("/me");
        const profile = await response.json();

        document.getElementById("profileName").value = profile.name || "";
        document.getElementById("profileEmail").value = profile.email || "";
        document.getElementById("profilePhone").value = profile.phone || "";
        document.getElementById("profileRole").value = profile.role || "customer";

        document.getElementById("profileModal").style.display = "flex";
    } catch (e) {
        console.error(e);
    }
}

function closeProfileModal() {
    document.getElementById("profileModal").style.display = "none";
}

document.getElementById("profileForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const submitBtn = document.getElementById("profileSubmitBtn");
    submitBtn.disabled = true;

    try {
        const updatedName = document.getElementById("profileName").value.trim();
        const updatedPhone = document.getElementById("profilePhone").value.trim();

        const response = await authFetch("/me", {
            method: "PUT",
            body: JSON.stringify({
                name: updatedName,
                phone: updatedPhone
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update profile");

        currentUser.name = result.customer.name;
        currentUser.phone = result.customer.phone;
        localStorage.setItem("customer", JSON.stringify(currentUser));

        showToast("Profile updated successfully!");
        updateNavbar();
        closeProfileModal();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
});


// ======================================
// 14. ADMIN DASHBOARD & OVERSIGHT
// ======================================

let currentAdminView = "overview";
let adminRoomsData = [];
let adminStaffData = [];
let adminHousekeepingData = [];

// Chart.js instances
let monthlyChartInstance = null;
let popularCategoriesChartInstance = null;
let housekeepingChartInstance = null;

// Search debounce timers
let bookingSearchTimer = null;
let customerSearchTimer = null;
let paymentSearchTimer = null;

function loadAdminDashboard() {
    if (!currentUser || currentUser.role !== "admin") {
        showToast("Administrator privileges required.", "error");
        showSection("home");
        return;
    }

    // Set admin user name in topbar
    const adminNameEl = document.getElementById("adminUserName");
    if (adminNameEl) adminNameEl.textContent = currentUser.name || "Administrator";

    // Load active view
    switchAdminView(currentAdminView);
}

function switchAdminView(viewId, clickedNavEl) {
    currentAdminView = viewId;

    // Update sidebar navigation pills
    document.querySelectorAll(".admin-nav-item").forEach(function (item) {
        item.classList.remove("active");
    });
    if (clickedNavEl) {
        clickedNavEl.classList.add("active");
    } else {
        const matchingNav = Array.from(document.querySelectorAll(".admin-nav-item")).find(function (item) {
            return item.getAttribute("onclick") && item.getAttribute("onclick").includes("'" + viewId + "'");
        });
        if (matchingNav) matchingNav.classList.add("active");
    }

    // Update view panels
    document.querySelectorAll(".admin-view-panel").forEach(function (panel) {
        panel.classList.remove("active");
    });
    const activePanel = document.getElementById("admin-view-" + viewId);
    if (activePanel) activePanel.classList.add("active");

    // Update topbar title
    const titles = {
        overview: "Dashboard Overview",
        rooms: "Room Catalog Management",
        bookings: "Guest Bookings & Reservations",
        customers: "Customer Accounts & Profiles",
        staff: "Hotel Staff Directory",
        housekeeping: "Housekeeping & Room Cleanliness",
        payments: "Payment Transactions & Settlements",
        analytics: "Reports & Performance Analytics",
        settings: "Hotel Configuration & Policies"
    };
    const titleEl = document.getElementById("adminViewTitle");
    if (titleEl) titleEl.textContent = titles[viewId] || "Admin Dashboard";

    // Load view data
    if (viewId === "overview") loadAdminOverview();
    else if (viewId === "rooms") loadAdminRooms();
    else if (viewId === "bookings") loadAdminBookings();
    else if (viewId === "customers") loadAdminCustomers();
    else if (viewId === "staff") loadAdminStaff();
    else if (viewId === "housekeeping") loadAdminHousekeeping();
    else if (viewId === "payments") loadAdminPayments();
    else if (viewId === "analytics") loadAdminAnalytics();
    else if (viewId === "settings") loadAdminSettings();
}

function refreshCurrentAdminView() {
    switchAdminView(currentAdminView);
    showToast("Dashboard data refreshed.", "success");
}


// --------------------------------------
// MODULE 0: OVERVIEW (8 DB STATS)
// --------------------------------------

async function loadAdminOverview() {
    try {
        const response = await authFetch("/admin/dashboard");
        const stats = await response.json();
        if (!response.ok) throw new Error(stats.detail || "Failed to load dashboard metrics");

        // 8 Database Statistics
        const grid = document.getElementById("adminOverviewStatsGrid");
        if (grid) {
            grid.innerHTML =
                '<div class="admin-stat-card">' +
                    '<span class="stat-icon">🏨</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.total_rooms + '</h3>' +
                        '<p>1. Total Rooms</p>' +
                        '<small>' + stats.available_rooms + ' available / ' + stats.occupied_rooms + ' occupied</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card stat-highlight-green">' +
                    '<span class="stat-icon">🟢</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.available_rooms + '</h3>' +
                        '<p>2. Available Rooms</p>' +
                        '<small>Ready for check-in</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card stat-highlight-orange">' +
                    '<span class="stat-icon">🟡</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.occupied_rooms + '</h3>' +
                        '<p>3. Occupied Rooms</p>' +
                        '<small>' + stats.occupancy_rate + '% occupancy rate</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card">' +
                    '<span class="stat-icon">👥</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.total_customers + '</h3>' +
                        '<p>4. Total Customers</p>' +
                        '<small>Registered accounts</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card">' +
                    '<span class="stat-icon">📋</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.total_bookings + '</h3>' +
                        '<p>5. Total Bookings</p>' +
                        '<small>Lifetime reservations</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card stat-highlight-gold">' +
                    '<span class="stat-icon">✅</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.confirmed_bookings + '</h3>' +
                        '<p>6. Confirmed Bookings</p>' +
                        '<small>Active & verified</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card stat-highlight-red">' +
                    '<span class="stat-icon">❌</span>' +
                    '<div class="stat-content">' +
                        '<h3>' + stats.cancelled_bookings + '</h3>' +
                        '<p>7. Cancelled Bookings</p>' +
                        '<small>Released back to inventory</small>' +
                    '</div>' +
                '</div>' +
                '<div class="admin-stat-card stat-revenue-card">' +
                    '<span class="stat-icon">💰</span>' +
                    '<div class="stat-content">' +
                        '<h3>₹' + Number(stats.total_revenue).toLocaleString("en-IN") + '</h3>' +
                        '<p>8. Total Revenue</p>' +
                        '<small>From completed payments</small>' +
                    '</div>' +
                '</div>';
        }

        // Occupancy gauge banner
        const occText = document.getElementById("overviewOccupancyText");
        const occFill = document.getElementById("overviewOccupancyFill");
        if (occText && occFill) {
            occText.textContent = stats.occupied_rooms + ' of ' + stats.total_rooms + ' rooms currently occupied (' + stats.occupancy_rate + '% capacity)';
            occFill.style.width = Math.min(100, stats.occupancy_rate) + '%';
        }

        // Load 5 recent bookings for the overview table
        loadOverviewRecentBookings();

    } catch (error) {
        console.error("Overview stats error:", error);
    }
}

async function loadOverviewRecentBookings() {
    try {
        const response = await authFetch("/admin/bookings");
        const bookings = await response.json();
        const tbody = document.getElementById("overviewRecentBookingsBody");
        if (!tbody) return;

        if (!Array.isArray(bookings) || bookings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No reservations recorded yet.</td></tr>';
            return;
        }

        const recent = bookings.slice(0, 5);
        tbody.innerHTML = recent.map(function (b) {
            const statusClass = b.status === "Confirmed" ? "status-confirmed" : "status-cancelled";
            const payClass = b.payment_status === "Completed" ? "status-confirmed" : "status-pending";
            return '<tr>' +
                '<td><strong>' + escapeHTML(b.booking_reference || ('#' + b.id)) + '</strong></td>' +
                '<td>' + escapeHTML(b.customer_name) + '</td>' +
                '<td>Room ' + escapeHTML(b.room_number) + ' (' + escapeHTML(b.room_type) + ')</td>' +
                '<td>' + b.check_in + ' → ' + b.check_out + '</td>' +
                '<td>₹' + Number(b.total_price).toLocaleString("en-IN") + '</td>' +
                '<td><span class="status-badge ' + payClass + '">' + escapeHTML(b.payment_status) + '</span></td>' +
                '<td><span class="status-badge ' + statusClass + '">' + escapeHTML(b.status) + '</span></td>' +
            '</tr>';
        }).join("");
    } catch (e) {
        console.error(e);
    }
}


// --------------------------------------
// MODULE 1: ROOM MANAGEMENT
// --------------------------------------

async function loadAdminRooms() {
    try {
        const response = await fetch(API + "/rooms");
        const rooms = await response.json();
        adminRoomsData = rooms;
        renderAdminRoomsTable(rooms);
    } catch (error) {
        console.error("Load rooms error:", error);
    }
}

function renderAdminRoomsTable(rooms) {
    const tbody = document.getElementById("adminRoomsBody");
    if (!tbody) return;

    if (!Array.isArray(rooms) || rooms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No rooms match your filter criteria.</td></tr>';
        return;
    }

    tbody.innerHTML = rooms.map(function (room) {
        const resStatusClass = room.status === "Available" ? "status-confirmed" : (room.status === "Occupied" ? "status-pending" : "status-cancelled");
        const hkStatus = room.housekeeping_status || "Clean";
        let hkBadgeClass = "hk-badge-clean";
        if (hkStatus === "Dirty") hkBadgeClass = "hk-badge-dirty";
        else if (hkStatus === "Cleaning in Progress") hkBadgeClass = "hk-badge-cleaning";
        else if (hkStatus === "Maintenance Required") hkBadgeClass = "hk-badge-maint";

        return '<tr>' +
            '<td><strong>' + escapeHTML(room.room_number) + '</strong></td>' +
            '<td>' + escapeHTML(room.room_type) + '</td>' +
            '<td>₹' + Number(room.price).toLocaleString("en-IN") + '</td>' +
            '<td>' + room.capacity + ' Guests</td>' +
            '<td><span class="status-badge ' + resStatusClass + '">' + escapeHTML(room.status) + '</span></td>' +
            '<td><span class="status-badge ' + hkBadgeClass + '">' + escapeHTML(hkStatus) + '</span></td>' +
            '<td>' +
                '<div class="table-actions-group">' +
                    '<button class="action-btn edit-btn" onclick="openEditRoom(' + room.id + ')">Edit</button>' +
                    '<button class="action-btn hk-btn" onclick="openEditHousekeeping(' + room.id + ', \'' + escapeHTML(room.room_number) + '\', \'' + escapeHTML(hkStatus) + '\')">Clean</button>' +
                    '<button class="action-btn delete-btn" onclick="deleteRoom(' + room.id + ')">Delete</button>' +
                '</div>' +
            '</td>' +
        '</tr>';
    }).join("");
}

function filterAdminRoomsTable() {
    const searchVal = (document.getElementById("adminRoomSearch").value || "").trim().toLowerCase();
    const typeVal = document.getElementById("adminRoomTypeFilter").value;
    const statusVal = document.getElementById("adminRoomStatusFilter").value;

    const filtered = adminRoomsData.filter(function (room) {
        const matchesSearch = !searchVal ||
            room.room_number.toLowerCase().includes(searchVal) ||
            (room.description || "").toLowerCase().includes(searchVal);
        const matchesType = !typeVal || room.room_type === typeVal;
        const matchesStatus = !statusVal || room.status === statusVal;
        return matchesSearch && matchesType && matchesStatus;
    });

    renderAdminRoomsTable(filtered);
}

function openAddRoom() { document.getElementById("addRoomModal").style.display = "flex"; }
function closeAddRoom() { document.getElementById("addRoomModal").style.display = "none"; }

document.getElementById("addRoomForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    const submitBtn = document.getElementById("addRoomSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/rooms", {
            method: "POST",
            body: JSON.stringify({
                room_number: document.getElementById("newRoomNumber").value.trim(),
                room_type: document.getElementById("newRoomType").value,
                price: Number(document.getElementById("newRoomPrice").value),
                capacity: Number(document.getElementById("newRoomCapacity").value),
                description: document.getElementById("newRoomDescription").value.trim(),
                image_url: document.getElementById("newRoomImage").value.trim()
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to add room");

        showToast("Room added successfully!");
        closeAddRoom();
        document.getElementById("addRoomForm").reset();
        loadAdminRooms();
        loadRooms();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
});

function openEditRoom(roomId) {
    const room = adminRoomsData.find(function (r) { return r.id === roomId; });
    if (!room) return;

    document.getElementById("editRoomId").value = room.id;
    document.getElementById("editRoomNumber").value = room.room_number;
    document.getElementById("editRoomType").value = room.room_type;
    document.getElementById("editRoomPrice").value = room.price;
    document.getElementById("editRoomCapacity").value = room.capacity;
    document.getElementById("editRoomStatus").value = room.status;
    document.getElementById("editRoomDescription").value = room.description || "";
    document.getElementById("editRoomImage").value = room.image_url || "";

    document.getElementById("editRoomModal").style.display = "flex";
}

function closeEditRoom() { document.getElementById("editRoomModal").style.display = "none"; }

async function submitEditRoom(event) {
    event.preventDefault();
    const roomId = document.getElementById("editRoomId").value;
    const submitBtn = document.getElementById("editRoomSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/rooms/" + roomId, {
            method: "PUT",
            body: JSON.stringify({
                room_number: document.getElementById("editRoomNumber").value.trim(),
                room_type: document.getElementById("editRoomType").value,
                price: Number(document.getElementById("editRoomPrice").value),
                capacity: Number(document.getElementById("editRoomCapacity").value),
                status: document.getElementById("editRoomStatus").value,
                description: document.getElementById("editRoomDescription").value.trim(),
                image_url: document.getElementById("editRoomImage").value.trim()
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update room");

        showToast("Room details updated successfully!");
        closeEditRoom();
        loadAdminRooms();
        loadRooms();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
}

async function deleteRoom(roomId) {
    if (!confirm("Are you sure you want to delete this room? This cannot be undone.")) return;

    try {
        const response = await authFetch("/rooms/" + roomId, { method: "DELETE" });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to delete room");

        showToast("Room deleted successfully.");
        loadAdminRooms();
        loadRooms();
    } catch (error) {
        showToast(error.message, "error");
    }
}


// --------------------------------------
// MODULE 2: BOOKING MANAGEMENT
// --------------------------------------

function debounceAdminBookingSearch() {
    clearTimeout(bookingSearchTimer);
    bookingSearchTimer = setTimeout(loadAdminBookings, 300);
}

async function loadAdminBookings() {
    const searchVal = (document.getElementById("adminBookingSearch").value || "").trim();
    const statusVal = document.getElementById("adminBookingStatusFilter").value;

    let url = "/admin/bookings?";
    if (searchVal) url += "search=" + encodeURIComponent(searchVal) + "&";
    if (statusVal) url += "status=" + encodeURIComponent(statusVal) + "&";

    try {
        const response = await authFetch(url);
        const bookings = await response.json();
        const tbody = document.getElementById("adminBookingsBody");
        if (!tbody) return;

        if (!Array.isArray(bookings) || bookings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No reservations match your search or filter.</td></tr>';
            return;
        }

        tbody.innerHTML = bookings.map(function (b) {
            const statusClass = b.status === "Confirmed" ? "status-confirmed" : (b.status === "Completed" ? "status-confirmed" : "status-cancelled");
            const payClass = b.payment_status === "Completed" ? "status-confirmed" : "status-pending";
            const cancelBtn = b.status === "Confirmed"
                ? '<button class="action-btn delete-btn" onclick="adminCancelBooking(' + b.id + ')">Cancel</button>'
                : '';

            return '<tr>' +
                '<td><strong>' + escapeHTML(b.booking_reference || ('#' + b.id)) + '</strong></td>' +
                '<td>' + escapeHTML(b.customer_name) + '<br><small style="color:#777;">' + escapeHTML(b.customer_email) + '</small></td>' +
                '<td>Room ' + escapeHTML(b.room_number) + ' (' + escapeHTML(b.room_type) + ')</td>' +
                '<td>' + b.check_in + ' → ' + b.check_out + '</td>' +
                '<td>' + (b.guests || 1) + '</td>' +
                '<td>₹' + Number(b.total_price).toLocaleString("en-IN") + '</td>' +
                '<td><span class="status-badge ' + payClass + '">' + escapeHTML(b.payment_status) + '</span></td>' +
                '<td><span class="status-badge ' + statusClass + '">' + escapeHTML(b.status) + '</span></td>' +
                '<td>' +
                    '<div class="table-actions-group">' +
                        '<button class="action-btn edit-btn" onclick="openAdminBookingDetails(' + b.id + ')">View</button>' +
                        cancelBtn +
                    '</div>' +
                '</td>' +
            '</tr>';
        }).join("");
    } catch (error) {
        console.error("Admin bookings error:", error);
    }
}

async function openAdminBookingDetails(bookingId) {
    try {
        const response = await authFetch("/bookings/" + bookingId);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Failed to load booking details");

        const card = document.getElementById("adminBookingDetailCard");
        card.innerHTML =
            '<div class="confirm-review-card">' +
                '<div class="review-row"><span class="review-label">Booking Reference</span><strong class="review-val">' + escapeHTML(data.booking_reference) + '</strong></div>' +
                '<div class="review-row"><span class="review-label">Customer Name</span><strong class="review-val">' + escapeHTML(data.customer.name) + '</strong></div>' +
                '<div class="review-row"><span class="review-label">Customer Email</span><span class="review-val">' + escapeHTML(data.customer.email) + '</span></div>' +
                '<div class="review-row"><span class="review-label">Customer Phone</span><span class="review-val">' + escapeHTML(data.customer.phone || 'N/A') + '</span></div>' +
                '<div class="review-row"><span class="review-label">Reserved Room</span><strong class="review-val">Room ' + escapeHTML(data.room.room_number) + ' (' + escapeHTML(data.room.room_type) + ')</strong></div>' +
                '<div class="review-row"><span class="review-label">Stay Dates</span><span class="review-val">' + data.check_in + ' to ' + data.check_out + ' (' + data.nights + ' nights)</span></div>' +
                '<div class="review-row"><span class="review-label">Guests</span><span class="review-val">' + data.guests + '</span></div>' +
                '<div class="review-row"><span class="review-label">Nightly Rate</span><span class="review-val">₹' + Number(data.nightly_rate).toLocaleString("en-IN") + '</span></div>' +
                '<div class="review-row review-total-row"><span class="review-label">Total Amount</span><strong class="review-val-total">₹' + Number(data.total_price).toLocaleString("en-IN") + '</strong></div>' +
                '<div class="review-row"><span class="review-label">Reservation Status</span><span class="status-badge ' + (data.status === "Confirmed" ? "status-confirmed" : "status-cancelled") + '">' + escapeHTML(data.status) + '</span></div>' +
                '<div class="review-row"><span class="review-label">Payment Status</span><span class="status-badge ' + (data.payment.payment_status === "Completed" ? "status-confirmed" : "status-pending") + '">' + escapeHTML(data.payment.payment_status) + '</span></div>' +
                '<div class="review-row"><span class="review-label">Payment Method</span><span class="review-val">' + escapeHTML(data.payment.payment_method) + '</span></div>' +
            '</div>' +
            '<div style="margin-top:20px; display:flex; gap:12px; justify-content:flex-end;">' +
                '<button class="secondary-btn small" onclick="openInvoiceModal(' + data.id + ')">🧾 View Invoice</button>' +
                (data.status === "Confirmed" ? '<button class="action-btn delete-btn" onclick="adminCancelBooking(' + data.id + '); closeAdminBookingDetails();">Cancel Booking</button>' : '') +
            '</div>';

        document.getElementById("adminBookingDetailsModal").style.display = "flex";
    } catch (e) {
        showToast(e.message, "error");
    }
}

function closeAdminBookingDetails() {
    document.getElementById("adminBookingDetailsModal").style.display = "none";
}

async function adminCancelBooking(bookingId) {
    if (!confirm("Are you sure you want to cancel booking #" + bookingId + "? Dates will be immediately freed.")) return;

    try {
        const response = await authFetch("/bookings/cancel/" + bookingId, { method: "PUT" });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Cancellation failed");

        showToast("Booking #" + bookingId + " cancelled.");
        loadAdminBookings();
        loadAdminOverview();
    } catch (error) {
        showToast(error.message, "error");
    }
}


// --------------------------------------
// MODULE 3: CUSTOMER MANAGEMENT
// --------------------------------------

function debounceAdminCustomerSearch() {
    clearTimeout(customerSearchTimer);
    customerSearchTimer = setTimeout(loadAdminCustomers, 300);
}

async function loadAdminCustomers() {
    const searchVal = (document.getElementById("adminCustomerSearch").value || "").trim();
    let url = "/admin/customers?";
    if (searchVal) url += "search=" + encodeURIComponent(searchVal);

    try {
        const response = await authFetch(url);
        const customers = await response.json();
        const tbody = document.getElementById("adminCustomersBody");
        if (!tbody) return;

        if (!Array.isArray(customers) || customers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No registered customers found.</td></tr>';
            return;
        }

        tbody.innerHTML = customers.map(function (c) {
            const dateStr = c.created_at ? c.created_at.split("T")[0] : "-";
            const statusClass = c.status === "Active" ? "status-confirmed" : "status-cancelled";
            const roleBadgeClass = c.role === "admin" ? "role-badge-admin" : "role-badge-cust";
            const toggleStatusBtn = c.id === currentUser.id
                ? '<span style="color:#aaa; font-size:12px;">(You)</span>'
                : '<button class="action-btn ' + (c.status === "Active" ? "delete-btn" : "pay-btn") + '" onclick="toggleCustomerStatus(' + c.id + ', \'' + escapeHTML(c.status) + '\')">' +
                    (c.status === "Active" ? "Deactivate" : "Activate") +
                  '</button>';

            return '<tr>' +
                '<td>#' + c.id + '</td>' +
                '<td><strong>' + escapeHTML(c.name) + '</strong></td>' +
                '<td>' + escapeHTML(c.email) + '</td>' +
                '<td>' + escapeHTML(c.phone || '-') + '</td>' +
                '<td><span class="role-badge ' + roleBadgeClass + '">' + escapeHTML(c.role) + '</span></td>' +
                '<td><span class="status-badge ' + statusClass + '">' + escapeHTML(c.status) + '</span></td>' +
                '<td>' + (c.total_bookings || 0) + '</td>' +
                '<td>' + dateStr + '</td>' +
                '<td>' +
                    '<div class="table-actions-group">' +
                        '<button class="action-btn edit-btn" onclick="openCustomerDetails(' + c.id + ')">History</button>' +
                        '<button class="action-btn edit-btn" onclick="openEditCustomer(' + c.id + ')">Edit</button>' +
                        toggleStatusBtn +
                    '</div>' +
                '</td>' +
            '</tr>';
        }).join("");
    } catch (error) {
        console.error("Admin customers error:", error);
    }
}

async function openCustomerDetails(customerId) {
    try {
        const response = await authFetch("/admin/customers/" + customerId);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Failed to load customer profile");

        document.getElementById("custDetailName").textContent = data.name;
        document.getElementById("custDetailContact").textContent = data.email + " • " + (data.phone || "No phone");
        document.getElementById("custDetailTotalSpent").textContent = "₹" + Number(data.total_spent).toLocaleString("en-IN") + " Total Spent";
        document.getElementById("custDetailBookingCount").textContent = data.total_bookings + " Reservations";

        const statusBadge = document.getElementById("custDetailStatus");
        statusBadge.textContent = data.status;
        statusBadge.className = "status-badge " + (data.status === "Active" ? "status-confirmed" : "status-cancelled");

        const tbody = document.getElementById("custDetailBookingsBody");
        if (data.bookings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No bookings recorded for this customer.</td></tr>';
        } else {
            tbody.innerHTML = data.bookings.map(function (b) {
                return '<tr>' +
                    '<td><strong>' + escapeHTML(b.booking_reference) + '</strong></td>' +
                    '<td>Room ' + escapeHTML(b.room_number) + ' (' + escapeHTML(b.room_type) + ')</td>' +
                    '<td>' + b.check_in + ' → ' + b.check_out + '</td>' +
                    '<td>₹' + Number(b.total_price).toLocaleString("en-IN") + '</td>' +
                    '<td><span class="status-badge ' + (b.payment_status === "Completed" ? "status-confirmed" : "status-pending") + '">' + escapeHTML(b.payment_status) + '</span></td>' +
                    '<td><span class="status-badge ' + (b.status === "Confirmed" ? "status-confirmed" : "status-cancelled") + '">' + escapeHTML(b.status) + '</span></td>' +
                '</tr>';
            }).join("");
        }

        document.getElementById("customerDetailsModal").style.display = "flex";
    } catch (e) {
        showToast(e.message, "error");
    }
}

function closeCustomerDetails() {
    document.getElementById("customerDetailsModal").style.display = "none";
}

async function openEditCustomer(customerId) {
    try {
        const response = await authFetch("/admin/customers/" + customerId);
        const c = await response.json();
        if (!response.ok) throw new Error(c.detail || "Failed to load customer details");

        document.getElementById("editCustomerId").value = c.id;
        document.getElementById("editCustomerName").value = c.name;
        document.getElementById("editCustomerEmail").value = c.email;
        document.getElementById("editCustomerPhone").value = c.phone || "";
        document.getElementById("editCustomerRole").value = c.role;
        document.getElementById("editCustomerStatus").value = c.status;

        document.getElementById("editCustomerModal").style.display = "flex";
    } catch (e) {
        showToast(e.message, "error");
    }
}

function closeEditCustomer() {
    document.getElementById("editCustomerModal").style.display = "none";
}

async function submitEditCustomer(event) {
    event.preventDefault();
    const customerId = document.getElementById("editCustomerId").value;
    const submitBtn = document.getElementById("editCustomerSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/admin/customers/" + customerId, {
            method: "PUT",
            body: JSON.stringify({
                name: document.getElementById("editCustomerName").value.trim(),
                phone: document.getElementById("editCustomerPhone").value.trim(),
                role: document.getElementById("editCustomerRole").value,
                status: document.getElementById("editCustomerStatus").value
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update customer");

        showToast("Customer account updated successfully!");
        closeEditCustomer();
        loadAdminCustomers();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
}

async function toggleCustomerStatus(customerId, currentStatus) {
    const newStatus = currentStatus === "Active" ? "Inactive" : "Active";
    const promptMsg = newStatus === "Inactive"
        ? "Deactivate this customer account? They will not be able to log in."
        : "Reactivate this customer account?";
    if (!confirm(promptMsg)) return;

    try {
        const response = await authFetch("/admin/customers/" + customerId + "/status", {
            method: "PUT",
            body: JSON.stringify({ status: newStatus })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update account status");

        showToast("Customer account " + (newStatus === "Active" ? "activated" : "deactivated") + ".");
        loadAdminCustomers();
    } catch (e) {
        showToast(e.message, "error");
    }
}


// --------------------------------------
// MODULE 4: STAFF MANAGEMENT
// --------------------------------------

async function loadAdminStaff() {
    try {
        const response = await authFetch("/admin/staff");
        const staff = await response.json();
        adminStaffData = staff;
        renderAdminStaffTable(staff);
    } catch (error) {
        console.error("Admin staff error:", error);
    }
}

function renderAdminStaffTable(staff) {
    const tbody = document.getElementById("adminStaffBody");
    if (!tbody) return;

    if (!Array.isArray(staff) || staff.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No staff members listed.</td></tr>';
        return;
    }

    tbody.innerHTML = staff.map(function (s) {
        const statusClass = s.status === "Active" ? "status-confirmed" : (s.status === "On Leave" ? "status-pending" : "status-cancelled");
        return '<tr>' +
            '<td>#' + s.id + '</td>' +
            '<td><strong>' + escapeHTML(s.name) + '</strong></td>' +
            '<td>' + escapeHTML(s.email) + '</td>' +
            '<td>' + escapeHTML(s.phone || '-') + '</td>' +
            '<td>' + escapeHTML(s.designation) + '</td>' +
            '<td><span class="status-badge ' + statusClass + '">' + escapeHTML(s.status) + '</span></td>' +
            '<td>' +
                '<div class="table-actions-group">' +
                    '<button class="action-btn edit-btn" onclick="openEditStaff(' + s.id + ')">Edit</button>' +
                    '<button class="action-btn delete-btn" onclick="deleteStaff(' + s.id + ')">Remove</button>' +
                '</div>' +
            '</td>' +
        '</tr>';
    }).join("");
}

function filterAdminStaffTable() {
    const searchVal = (document.getElementById("adminStaffSearch").value || "").trim().toLowerCase();
    const filtered = adminStaffData.filter(function (s) {
        return !searchVal ||
            s.name.toLowerCase().includes(searchVal) ||
            s.designation.toLowerCase().includes(searchVal) ||
            s.email.toLowerCase().includes(searchVal);
    });
    renderAdminStaffTable(filtered);
}

function openAddStaff() { document.getElementById("addStaffModal").style.display = "flex"; }
function closeAddStaff() { document.getElementById("addStaffModal").style.display = "none"; }

document.getElementById("addStaffForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    const submitBtn = document.getElementById("addStaffSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/admin/staff", {
            method: "POST",
            body: JSON.stringify({
                name: document.getElementById("newStaffName").value.trim(),
                email: document.getElementById("newStaffEmail").value.trim(),
                phone: document.getElementById("newStaffPhone").value.trim(),
                designation: document.getElementById("newStaffDesignation").value,
                status: document.getElementById("newStaffStatus").value
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to add staff");

        showToast("Staff member added successfully!");
        closeAddStaff();
        document.getElementById("addStaffForm").reset();
        loadAdminStaff();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
});

function openEditStaff(staffId) {
    const s = adminStaffData.find(function (item) { return item.id === staffId; });
    if (!s) return;

    document.getElementById("editStaffId").value = s.id;
    document.getElementById("editStaffName").value = s.name;
    document.getElementById("editStaffEmail").value = s.email;
    document.getElementById("editStaffPhone").value = s.phone || "";
    document.getElementById("editStaffDesignation").value = s.designation;
    document.getElementById("editStaffStatus").value = s.status;

    document.getElementById("editStaffModal").style.display = "flex";
}

function closeEditStaff() { document.getElementById("editStaffModal").style.display = "none"; }

async function submitEditStaff(event) {
    event.preventDefault();
    const staffId = document.getElementById("editStaffId").value;
    const submitBtn = document.getElementById("editStaffSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/admin/staff/" + staffId, {
            method: "PUT",
            body: JSON.stringify({
                name: document.getElementById("editStaffName").value.trim(),
                phone: document.getElementById("editStaffPhone").value.trim(),
                designation: document.getElementById("editStaffDesignation").value,
                status: document.getElementById("editStaffStatus").value
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update staff info");

        showToast("Staff details updated!");
        closeEditStaff();
        loadAdminStaff();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
}

async function deleteStaff(staffId) {
    if (!confirm("Remove this staff member from the directory?")) return;

    try {
        const response = await authFetch("/admin/staff/" + staffId, { method: "DELETE" });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to delete staff");

        showToast("Staff member removed.");
        loadAdminStaff();
    } catch (e) {
        showToast(e.message, "error");
    }
}


// --------------------------------------
// MODULE 5: HOUSEKEEPING MODULE
// --------------------------------------

async function loadAdminHousekeeping() {
    try {
        const response = await authFetch("/admin/housekeeping");
        const rooms = await response.json();
        adminHousekeepingData = rooms;

        // Compute cleaning counts
        let clean = 0, dirty = 0, cleaning = 0, maint = 0;
        rooms.forEach(function (r) {
            const s = r.housekeeping_status || "Clean";
            if (s === "Clean") clean++;
            else if (s === "Dirty") dirty++;
            else if (s === "Cleaning in Progress") cleaning++;
            else if (s === "Maintenance Required") maint++;
        });

        const cEl = document.getElementById("hkCleanCount");
        const dEl = document.getElementById("hkDirtyCount");
        const clEl = document.getElementById("hkCleaningCount");
        const mEl = document.getElementById("hkMaintenanceCount");
        if (cEl) cEl.textContent = clean;
        if (dEl) dEl.textContent = dirty;
        if (clEl) clEl.textContent = cleaning;
        if (mEl) mEl.textContent = maint;

        renderAdminHousekeepingTable(rooms);
    } catch (e) {
        console.error("Admin housekeeping error:", e);
    }
}

function renderAdminHousekeepingTable(rooms) {
    const tbody = document.getElementById("adminHousekeepingBody");
    if (!tbody) return;

    if (!Array.isArray(rooms) || rooms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No rooms match filter.</td></tr>';
        return;
    }

    tbody.innerHTML = rooms.map(function (r) {
        const hkStatus = r.housekeeping_status || "Clean";
        let hkBadgeClass = "hk-badge-clean";
        if (hkStatus === "Dirty") hkBadgeClass = "hk-badge-dirty";
        else if (hkStatus === "Cleaning in Progress") hkBadgeClass = "hk-badge-cleaning";
        else if (hkStatus === "Maintenance Required") hkBadgeClass = "hk-badge-maint";

        const resStatusClass = r.status === "Available" ? "status-confirmed" : (r.status === "Occupied" ? "status-pending" : "status-cancelled");
        const occupantStr = r.current_guest
            ? '<strong>' + escapeHTML(r.current_guest.name) + '</strong><br><small style="color:#777;">Check-out: ' + r.current_guest.check_out + '</small>'
            : '<span style="color:#999;">Vacant</span>';

        const lastCleanedStr = r.last_cleaned ? new Date(r.last_cleaned).toLocaleString() : "Never recorded";

        return '<tr>' +
            '<td><strong>' + escapeHTML(r.room_number) + '</strong></td>' +
            '<td>' + escapeHTML(r.room_type) + '</td>' +
            '<td><span class="status-badge ' + resStatusClass + '">' + escapeHTML(r.status) + '</span></td>' +
            '<td>' + occupantStr + '</td>' +
            '<td><span class="status-badge ' + hkBadgeClass + '">' + escapeHTML(hkStatus) + '</span></td>' +
            '<td><small>' + lastCleanedStr + '</small></td>' +
            '<td>' +
                '<button class="action-btn hk-btn" onclick="openEditHousekeeping(' + r.id + ', \'' + escapeHTML(r.room_number) + '\', \'' + escapeHTML(hkStatus) + '\')">' +
                    'Change Status' +
                '</button>' +
            '</td>' +
        '</tr>';
    }).join("");
}

function filterAdminHousekeepingTable() {
    const searchVal = (document.getElementById("adminHkSearch").value || "").trim().toLowerCase();
    const filterVal = document.getElementById("adminHkFilter").value;

    const filtered = adminHousekeepingData.filter(function (r) {
        const matchesSearch = !searchVal ||
            r.room_number.toLowerCase().includes(searchVal) ||
            r.room_type.toLowerCase().includes(searchVal);
        const matchesStatus = !filterVal || (r.housekeeping_status || "Clean") === filterVal;
        return matchesSearch && matchesStatus;
    });

    renderAdminHousekeepingTable(filtered);
}

function openEditHousekeeping(roomId, roomNumber, currentStatus) {
    document.getElementById("hkModalRoomId").value = roomId;
    document.getElementById("hkModalRoomTag").textContent = "Room " + roomNumber + " — Current: " + currentStatus;
    document.getElementById("hkModalStatus").value = currentStatus;
    document.getElementById("editHousekeepingModal").style.display = "flex";
}

function closeEditHousekeeping() {
    document.getElementById("editHousekeepingModal").style.display = "none";
}

async function submitEditHousekeeping(event) {
    event.preventDefault();
    const roomId = document.getElementById("hkModalRoomId").value;
    const newStatus = document.getElementById("hkModalStatus").value;
    const submitBtn = document.getElementById("hkModalSubmitBtn");
    submitBtn.disabled = true;

    try {
        const response = await authFetch("/admin/housekeeping/" + roomId, {
            method: "PUT",
            body: JSON.stringify({ housekeeping_status: newStatus })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to update housekeeping");

        showToast("Room housekeeping updated to '" + newStatus + "'!");
        closeEditHousekeeping();
        loadAdminHousekeeping();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        submitBtn.disabled = false;
    }
}


// --------------------------------------
// MODULE 6: PAYMENT MANAGEMENT
// --------------------------------------

function debounceAdminPaymentSearch() {
    clearTimeout(paymentSearchTimer);
    paymentSearchTimer = setTimeout(loadAdminPayments, 300);
}

async function loadAdminPayments() {
    const searchVal = (document.getElementById("adminPaymentSearch").value || "").trim();
    const statusVal = document.getElementById("adminPaymentStatusFilter").value;

    let url = "/admin/payments?";
    if (searchVal) url += "search=" + encodeURIComponent(searchVal) + "&";
    if (statusVal) url += "status=" + encodeURIComponent(statusVal) + "&";

    try {
        const response = await authFetch(url);
        const payments = await response.json();
        const tbody = document.getElementById("adminPaymentsBody");
        if (!tbody) return;

        if (!Array.isArray(payments) || payments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No payment records found.</td></tr>';
            return;
        }

        tbody.innerHTML = payments.map(function (p) {
            const pClass = p.payment_status === "Completed" ? "status-confirmed" : (p.payment_status === "Pending" ? "status-pending" : "status-cancelled");
            let toggleBtn = "-";
            if (p.payment_status === "Pending") {
                toggleBtn = '<button class="action-btn pay-btn" onclick="updatePaymentStatus(' + p.id + ', \'Completed\')">Mark Paid</button>';
            }

            const dateStr = p.payment_date ? p.payment_date.split("T")[0] : "-";

            return '<tr>' +
                '<td>#' + p.id + '</td>' +
                '<td><strong>' + escapeHTML(p.booking_reference || ('#' + p.booking_id)) + '</strong></td>' +
                '<td>' + escapeHTML(p.customer_name) + '<br><small style="color:#777;">' + escapeHTML(p.customer_email) + '</small></td>' +
                '<td>Room ' + escapeHTML(p.room_number) + '</td>' +
                '<td>₹' + Number(p.amount).toLocaleString("en-IN") + '</td>' +
                '<td>' + escapeHTML(p.payment_method) + '</td>' +
                '<td><code>' + escapeHTML(p.transaction_ref) + '</code></td>' +
                '<td><span class="status-badge ' + pClass + '">' + escapeHTML(p.payment_status) + '</span></td>' +
                '<td>' + dateStr + '</td>' +
                '<td>' + toggleBtn + '</td>' +
            '</tr>';
        }).join("");
    } catch (error) {
        console.error("Admin payments error:", error);
    }
}

async function updatePaymentStatus(paymentId, newStatus) {
    try {
        const response = await authFetch("/admin/payments/" + paymentId + "/status", {
            method: "PUT",
            body: JSON.stringify({ payment_status: newStatus })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Update failed");

        showToast("Payment status updated to '" + newStatus + "'.");
        loadAdminPayments();
        loadAdminOverview();
    } catch (e) {
        showToast(e.message, "error");
    }
}


// --------------------------------------
// MODULE 7: REPORTS AND ANALYTICS
// --------------------------------------

async function loadAdminAnalytics() {
    try {
        const response = await authFetch("/admin/analytics");
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Failed to load analytics");

        // KPI cards
        const occRateEl = document.getElementById("analyticsOccupancyRate");
        const revEl = document.getElementById("analyticsTotalRevenue");
        const guestsEl = document.getElementById("analyticsTotalGuests");
        const repeatEl = document.getElementById("analyticsRepeatGuests");

        if (occRateEl) occRateEl.textContent = data.occupancy.occupancy_rate + "%";
        if (guestsEl) guestsEl.textContent = data.customer_statistics.total_customers;
        if (repeatEl) repeatEl.textContent = data.customer_statistics.repeat_customers;

        // Also fetch revenue from dashboard endpoint
        const dashRes = await authFetch("/admin/dashboard");
        const dashData = await dashRes.json();
        if (revEl && dashData.total_revenue !== undefined) {
            revEl.textContent = "₹" + Number(dashData.total_revenue).toLocaleString("en-IN");
        }

        // Render Charts using Chart.js
        renderAnalyticsCharts(data);

    } catch (e) {
        console.error("Analytics load error:", e);
    }
}

function renderAnalyticsCharts(data) {
    if (typeof Chart === "undefined") {
        console.warn("Chart.js is not loaded yet.");
        return;
    }

    // Chart 1: Monthly Trends (Revenue & Bookings)
    const ctxMonthly = document.getElementById("monthlyTrendChart");
    if (ctxMonthly) {
        if (monthlyChartInstance) monthlyChartInstance.destroy();

        const labels = data.monthly_trends.map(function (m) { return m.month; });
        const revenues = data.monthly_trends.map(function (m) { return m.revenue; });
        const bookings = data.monthly_trends.map(function (m) { return m.bookings; });

        monthlyChartInstance = new Chart(ctxMonthly, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Revenue (₹)",
                        data: revenues,
                        borderColor: "#b77b38",
                        backgroundColor: "rgba(183, 123, 56, 0.15)",
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: "y"
                    },
                    {
                        label: "Confirmed Bookings",
                        data: bookings,
                        borderColor: "#173f35",
                        backgroundColor: "rgba(23, 63, 53, 0.15)",
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: "y1"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: "linear",
                        display: true,
                        position: "left",
                        title: { display: true, text: "Revenue (₹)" },
                        ticks: {
                            callback: function (val) { return "₹" + val.toLocaleString("en-IN"); }
                        }
                    },
                    y1: {
                        type: "linear",
                        display: true,
                        position: "right",
                        title: { display: true, text: "Bookings" },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // Chart 2: Popular Categories (Doughnut)
    const ctxCategories = document.getElementById("popularCategoriesChart");
    if (ctxCategories) {
        if (popularCategoriesChartInstance) popularCategoriesChartInstance.destroy();

        const catLabels = data.popular_categories.map(function (c) { return c.category; });
        const catBookings = data.popular_categories.map(function (c) { return c.total_bookings; });

        popularCategoriesChartInstance = new Chart(ctxCategories, {
            type: "doughnut",
            data: {
                labels: catLabels.length > 0 ? catLabels : ["Standard", "Deluxe", "Suite"],
                datasets: [{
                    data: catBookings.length > 0 ? catBookings : [0, 0, 0],
                    backgroundColor: ["#173f35", "#b77b38", "#4e7d70", "#d1a364"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom" }
                }
            }
        });
    }

    // Chart 3: Housekeeping Cleanliness (Pie)
    const ctxHousekeeping = document.getElementById("housekeepingChart");
    if (ctxHousekeeping) {
        if (housekeepingChartInstance) housekeepingChartInstance.destroy();

        const hkData = data.housekeeping_breakdown || {};
        const hkLabels = Object.keys(hkData);
        const hkCounts = Object.values(hkData);

        housekeepingChartInstance = new Chart(ctxHousekeeping, {
            type: "pie",
            data: {
                labels: hkLabels,
                datasets: [{
                    data: hkCounts,
                    backgroundColor: ["#2e7d32", "#c62828", "#f57c00", "#6a1b9a"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom" }
                }
            }
        });
    }
}


// --------------------------------------
// MODULE 8: HOTEL SETTINGS
// --------------------------------------

async function loadAdminSettings() {
    try {
        const response = await authFetch("/admin/settings");
        const settings = await response.json();
        if (!response.ok) throw new Error(settings.detail || "Failed to load settings");

        document.getElementById("setHotelName").value = settings.hotel_name || "";
        document.getElementById("setContactEmail").value = settings.contact_email || "";
        document.getElementById("setContactPhone").value = settings.contact_phone || "";
        document.getElementById("setHotelAddress").value = settings.hotel_address || "";
        document.getElementById("setCheckInTime").value = settings.check_in_time || "14:00";
        document.getElementById("setCheckOutTime").value = settings.check_out_time || "11:00";
        document.getElementById("setCancellationPolicy").value = settings.cancellation_policy || "";

        const badge = document.getElementById("adminHotelBadge");
        if (badge && settings.hotel_name) badge.textContent = settings.hotel_name;

        const updatedEl = document.getElementById("settingsLastUpdated");
        if (updatedEl && settings.updated_at) {
            updatedEl.textContent = "Last saved: " + new Date(settings.updated_at).toLocaleString();
        }
    } catch (e) {
        console.error("Settings load error:", e);
    }
}

async function saveHotelSettings(event) {
    event.preventDefault();
    const btn = document.getElementById("saveSettingsBtn");
    btn.disabled = true;

    try {
        const response = await authFetch("/admin/settings", {
            method: "PUT",
            body: JSON.stringify({
                hotel_name: document.getElementById("setHotelName").value.trim(),
                contact_email: document.getElementById("setContactEmail").value.trim(),
                contact_phone: document.getElementById("setContactPhone").value.trim(),
                hotel_address: document.getElementById("setHotelAddress").value.trim(),
                check_in_time: document.getElementById("setCheckInTime").value.trim(),
                check_out_time: document.getElementById("setCheckOutTime").value.trim(),
                cancellation_policy: document.getElementById("setCancellationPolicy").value.trim()
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Failed to save hotel settings");

        showToast("Hotel configuration and policies updated successfully!");
        loadAdminSettings();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
    }
}


// ======================================
// 16. CHATBOT ASSISTANT (FASTAPI BACKEND POWERED)
// ======================================

function toggleChat() {
    const chat = document.getElementById("chatWindow");
    if (!chat) return;
    const isVisible = chat.classList.contains("active") || chat.style.display === "flex";
    if (isVisible) {
        chat.classList.remove("active");
        chat.style.display = "none";
    } else {
        chat.classList.add("active");
        chat.style.display = "flex";
        setTimeout(() => {
            const input = document.getElementById("chatInput");
            if (input) input.focus();
        }, 150);
    }
}

function formatChatTime(date = new Date()) {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    const minsStr = minutes < 10 ? "0" + minutes : minutes;
    return `${hours}:${minsStr} ${ampm}`;
}

function addChatMessage(message, sender = "bot", quickReplies = null) {
    const container = document.getElementById("chatMessages");
    if (!container) return;

    const wrapper = document.createElement("div");
    wrapper.className = `chat-bubble-wrapper ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = sender === "user" ? "user-message" : "bot-message";

    const p = document.createElement("p");
    p.textContent = message;
    bubble.appendChild(p);

    const timeSpan = document.createElement("span");
    timeSpan.className = "chat-msg-time";
    timeSpan.textContent = formatChatTime(new Date());
    bubble.appendChild(timeSpan);

    wrapper.appendChild(bubble);
    container.appendChild(wrapper);

    if (quickReplies && Array.isArray(quickReplies) && quickReplies.length > 0) {
        const qrContainer = document.createElement("div");
        qrContainer.className = "chat-quick-actions";
        quickReplies.forEach(qrText => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = qrText;
            btn.onclick = () => quickChat(qrText);
            qrContainer.appendChild(btn);
        });
        container.appendChild(qrContainer);
    }

    container.scrollTop = container.scrollHeight;
}

function showChatTyping(show = true) {
    const typing = document.getElementById("chatTyping");
    if (typing) {
        typing.style.display = show ? "flex" : "none";
        if (show) {
            const container = document.getElementById("chatMessages");
            if (container) container.scrollTop = container.scrollHeight;
        }
    }
}

async function sendChatMessage(messageText) {
    const cleanMsg = (messageText || "").trim();
    if (!cleanMsg) return;

    addChatMessage(cleanMsg, "user");

    const input = document.getElementById("chatInput");
    if (input) input.value = "";

    showChatTyping(true);

    try {
        const token = localStorage.getItem("token");
        const headers = { "Content-Type": "application/json" };
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const userName = currentUser ? currentUser.name : null;

        const response = await fetch(`${API}/chat`, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({
                message: cleanMsg,
                user_name: userName
            })
        });

        if (response.status === 429) {
            showChatTyping(false);
            addChatMessage("You are sending messages too quickly. Please pause for a moment and try again.", "bot", ["Explore Rooms", "Check Prices"]);
            return;
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || "Unable to reach assistant backend.");
        }

        const data = await response.json();
        showChatTyping(false);

        addChatMessage(data.reply, "bot", data.quick_replies);

        if (data.action === "navigate:rooms") {
            const roomsSection = document.getElementById("rooms");
            if (roomsSection) {
                // Keep chat open but can scroll gently
            }
        } else if (data.action === "open:auth" && !currentUser) {
            openAuthModal("login");
        } else if (data.action === "navigate:my-bookings" && currentUser) {
            showSection("bookings");
        }
    } catch (err) {
        showChatTyping(false);
        addChatMessage(
            "I'm having a brief connection issue with our server. However, you can explore our rooms in the catalog, view pricing, or check your reservations from the top navigation bar!",
            "bot",
            ["Explore Rooms", "Check Prices", "Cancellation Policy"]
        );
    }
}

function quickChat(text) {
    sendChatMessage(text);
}

function handleChatSubmit(event) {
    if (event) event.preventDefault();
    const input = document.getElementById("chatInput");
    if (!input) return;
    sendChatMessage(input.value);
}

function clearChatHistory() {
    const container = document.getElementById("chatMessages");
    if (!container) return;
    const nowStr = formatChatTime(new Date());
    container.innerHTML = `
        <div class="chat-bubble-wrapper bot">
            <div class="bot-message">
                <p>Chat cleared! Welcome to <strong>StayEase Hotel &amp; Luxury Suites</strong>. How may I assist you with your stay today?</p>
                <span class="chat-msg-time">${nowStr}</span>
            </div>
        </div>
        <div class="chat-quick-actions" id="chatQuickActions">
            <button type="button" onclick="quickChat('Explore Rooms')">🏨 Explore Rooms</button>
            <button type="button" onclick="quickChat('What are your room prices?')">💰 Check Prices</button>
            <button type="button" onclick="quickChat('How do I book a room?')">📋 Booking Help</button>
            <button type="button" onclick="quickChat('What is your cancellation policy?')">🛡️ Cancellation Policy</button>
            <button type="button" onclick="quickChat('How can I contact customer support?')">📞 Contact Support</button>
        </div>
    `;
    showToast("Chat conversation cleared.", "info");
}


// ======================================
// 17. PASSWORD STRENGTH METER & SPA NAVIGATION
// ======================================

function checkPasswordStrength() {
    if (authMode !== "register") return;

    const password = document.getElementById("password").value;
    const strengthDiv = document.getElementById("passwordStrength");
    const bar = document.getElementById("strengthBar");
    const text = document.getElementById("strengthText");

    if (!password) {
        strengthDiv.classList.add("hidden");
        return;
    }

    strengthDiv.classList.remove("hidden");

    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*()_+\-=]/.test(password);
    const isLong = password.length >= 8;

    if (!isLong) {
        bar.className = "strength-bar strength-weak";
        text.textContent = "Weak — minimum 8 characters";
    } else if (hasUpper && hasLower && hasNumber && hasSpecial) {
        bar.className = "strength-bar strength-strong";
        text.textContent = "Strong password";
    } else {
        bar.className = "strength-bar strength-medium";
        text.textContent = "Medium — add uppercase, numbers, and symbols";
    }
}

function quickFilterCategory(category, btn) {
    document.querySelectorAll(".cat-pill").forEach(function (p) {
        p.classList.remove("active");
    });
    if (btn) btn.classList.add("active");

    const roomFilter = document.getElementById("roomFilter");
    if (roomFilter) roomFilter.value = category;

    searchRooms();
}

function submitContactForm(event) {
    event.preventDefault();
    const btn = document.getElementById("contactSubmitBtn");
    btn.disabled = true;
    btn.innerHTML = '✉️ Sending...';

    const name = document.getElementById("contactName").value.trim();

    setTimeout(function () {
        showToast("Thank you, " + name + "! Your inquiry has been forwarded to our 24/7 concierge desk.", "success");
        document.getElementById("contactForm").reset();
        btn.disabled = false;
        btn.innerHTML = '✉️ Submit Inquiry';
    }, 600);
}

function showSection(section) {
    const homeSections = document.querySelectorAll(".home-section");
    const myBookingsEl = document.getElementById("myBookingsSection");
    const adminEl = document.getElementById("adminSection");

    homeSections.forEach(function (el) { el.classList.add("hidden"); });
    myBookingsEl.classList.add("hidden");
    adminEl.classList.add("hidden");

    if (section === "home") {
        homeSections.forEach(function (el) { el.classList.remove("hidden"); });
        window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (section === "rooms") {
        homeSections.forEach(function (el) { el.classList.remove("hidden"); });
        setTimeout(function () {
            document.getElementById("rooms").scrollIntoView({ behavior: "smooth" });
        }, 100);
    } else if (section === "about") {
        homeSections.forEach(function (el) { el.classList.remove("hidden"); });
        setTimeout(function () {
            document.getElementById("about").scrollIntoView({ behavior: "smooth" });
        }, 100);
    } else if (section === "contact") {
        homeSections.forEach(function (el) { el.classList.remove("hidden"); });
        setTimeout(function () {
            document.getElementById("contact").scrollIntoView({ behavior: "smooth" });
        }, 100);
    } else if (section === "my-bookings") {
        myBookingsEl.classList.remove("hidden");
        window.scrollTo({ top: 0 });
        loadMyBookings();
    } else if (section === "admin") {
        if (!currentUser || currentUser.role !== "admin") {
            showToast("Administrator privileges required.", "error");
            showSection("home");
            return;
        }
        adminEl.classList.remove("hidden");
        window.scrollTo({ top: 0 });
        loadAdminDashboard();
    }

    document.getElementById("navMenu").classList.remove("active");
}

window.addEventListener("scroll", function () {
    const navbar = document.getElementById("siteNavbar");
    if (navbar) {
        if (window.scrollY > 40) navbar.classList.add("scrolled");
        else navbar.classList.remove("scrolled");
    }
});

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };
        return entities[character];
    });
}

function toggleMenu() {
    document.getElementById("navMenu").classList.toggle("active");
}

function setMinDates() {
    const today = new Date().toISOString().split("T")[0];
    const checkInInput = document.getElementById("checkIn");
    const checkOutInput = document.getElementById("checkOut");

    checkInInput.min = today;
    checkInInput.addEventListener("change", function () {
        if (this.value) {
            const nextDay = new Date(this.value);
            nextDay.setDate(nextDay.getDate() + 1);
            checkOutInput.min = nextDay.toISOString().split("T")[0];
            if (checkOutInput.value && checkOutInput.value <= this.value) {
                checkOutInput.value = "";
            }
        }
    });
}

function initializeWebsite() {
    updateNavbar();
    loadRooms();
    setMinDates();
}

document.addEventListener("DOMContentLoaded", initializeWebsite);
