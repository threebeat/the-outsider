// static/game.js

console.log('Game.js loaded successfully');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Socket.IO connection...');
    
    // Force WebSocket transport for better performance on Render
    const socket = io({ transports: ['websocket'] });
    console.log('Socket.IO connection created');
    
    let myUsername = null;
    let selectedVoteTarget = null;
    let isSpectator = false;
    let isTyping = false;
    let typingTimeout = null;

    // --- DOM Elements ---
    const log = document.getElementById('log');
    const playerList = document.getElementById('player-list');
    const turnIndicator = document.getElementById('turn-indicator');
    const myRole = document.getElementById('my-role');
    const myLocation = document.getElementById('my-location');
    const questionCounter = document.getElementById('question-counter');
    const questionCount = document.getElementById('question-count');
    const questionsUntilVote = document.getElementById('questions-until-vote');
    
    const loginForm = document.getElementById('login-form');
    const gameForms = document.getElementById('game-forms');
    const askForm = document.getElementById('ask-form');
    const answerForm = document.getElementById('answer-form');
    const voteForm = document.getElementById('vote-form');
    const voteOptions = document.getElementById('vote-options');
    const submitVoteBtn = document.getElementById('submit-vote-btn');
    
    const usernameInput = document.getElementById('username');
    const joinBtn = document.getElementById('join-btn');
    const startGameBtn = document.getElementById('start-game-btn');
    const manualResetBtn = document.getElementById('manual-reset-btn');
    
    const questionInput = document.getElementById('question-input');
    const targetPlayerSelect = document.getElementById('target-player-select');
    const askBtn = document.getElementById('ask-btn');
    const answerInput = document.getElementById('answer-input');
    const answerBtn = document.getElementById('answer-btn');

    const winCounter = document.getElementById('win-counter');
    const humanWinsDisplay = document.querySelector('.human-wins');
    const aiWinsDisplay = document.querySelector('.ai-wins');

    console.log('DOM elements found:', {
        log: !!log,
        playerList: !!playerList,
        loginForm: !!loginForm,
        gameForms: !!gameForms,
        voteForm: !!voteForm
    });

    // Add typing event listeners
    questionInput.addEventListener('input', startTyping);
    answerInput.addEventListener('input', startTyping);
    questionInput.addEventListener('blur', stopTyping);
    answerInput.addEventListener('blur', stopTyping);

    // --- Event Listeners ---
    
    // Typing indicator functions
    function startTyping() {
        if (!isTyping) {
            isTyping = true;
            socket.emit('typing_start', { username: myUsername });
        }
        // Clear existing timeout
        if (typingTimeout) {
            clearTimeout(typingTimeout);
        }
        // Set new timeout
        typingTimeout = setTimeout(stopTyping, 2000);
    }
    
    function stopTyping() {
        if (isTyping) {
            isTyping = false;
            socket.emit('typing_stop', { username: myUsername });
        }
        if (typingTimeout) {
            clearTimeout(typingTimeout);
            typingTimeout = null;
        }
    }
    
    joinBtn.addEventListener('click', () => {
        console.log('Join button clicked');
        myUsername = usernameInput.value.trim();
        if (myUsername) {
            console.log('Joining with username:', myUsername);
            socket.emit('join', { username: myUsername });
            loginForm.classList.add('hidden');
            gameForms.classList.remove('hidden');
        }
    });

    startGameBtn.addEventListener('click', () => {
        console.log('=== START GAME BUTTON CLICKED ===');
        console.log('Button disabled state:', startGameBtn.disabled);
        console.log('Current time:', Date.now());
        
        if (startGameBtn.disabled) {
            console.log('Start button is disabled, ignoring click');
            return;
        }
        
        console.log('Emitting start_game event...');
        socket.emit('start_game', {});
        
        // Disable button to prevent multiple clicks
        startGameBtn.disabled = true;
        console.log('Start button disabled after click');
    });

    manualResetBtn.addEventListener('click', () => {
        console.log('Manual reset button clicked');
        if (confirm('Are you sure you want to reset the game? This will clear all data and allow new players to join.')) {
            socket.emit('manual_reset');
        }
    });

    askBtn.addEventListener('click', () => {
        console.log('=== ASK BUTTON CLICKED ===');
        console.log('Is spectator:', isSpectator);
        console.log('Question input value:', questionInput.value);
        console.log('Target select value:', targetPlayerSelect.value);
        
        if (isSpectator) return; // Spectators can't ask questions
        const question = questionInput.value.trim();
        const target = targetPlayerSelect.value;
        console.log('Question submission - Available targets:', Array.from(targetPlayerSelect.options).map(opt => opt.value));
        console.log('Selected target:', target);
        console.log('My username:', myUsername);
        if (question && target) {
            console.log('Asking question:', question, 'to:', target);
            const questionData = { question, target };
            console.log('Emitting ask_question with data:', questionData);
            socket.emit('ask_question', questionData);
            console.log('ask_question event emitted');
            
            // Clear form and disable inputs immediately after submitting
            questionInput.value = '';
            askForm.classList.add('hidden');
            questionInput.disabled = true;
            targetPlayerSelect.disabled = true;
            askBtn.disabled = true;
            
            // Stop typing indicator
            stopTyping();
            
            // Update turn indicator to show question was sent
            turnIndicator.textContent = `Question sent to ${target}!`;
            turnIndicator.style.color = '#4caf50';
        } else {
            console.log('Question submission failed - question:', question, 'target:', target);
        }
    });
    
    answerBtn.addEventListener('click', () => {
        if (isSpectator) return; // Spectators can't answer
        const answer = answerInput.value.trim();
        if (answer) {
            console.log('Submitting answer:', answer);
            socket.emit('submit_answer', { answer });
            
            // Clear form and disable inputs immediately after submitting
            answerInput.value = '';
            answerForm.classList.add('hidden');
            answerInput.disabled = true;
            answerBtn.disabled = true;
            
            // Stop typing indicator
            stopTyping();
            
            // Update turn indicator to show answer was sent
            turnIndicator.textContent = 'Answer sent!';
            turnIndicator.style.color = '#4caf50';
        }
    });

    submitVoteBtn.addEventListener('click', () => {
        if (isSpectator) return; // Spectators can't vote
        if (selectedVoteTarget) {
            console.log('Submitting vote for:', selectedVoteTarget);
            socket.emit('submit_vote', { voted_for_sid: selectedVoteTarget });
            submitVoteBtn.disabled = true;
            submitVoteBtn.textContent = 'Vote Submitted';
        }
    });

    askForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const question = questionInput.value.trim();
        const target = targetPlayerSelect.value;
        if (!question || !target) return;
        socket.emit('submit_question', { question, target });
        questionInput.value = '';
        // Hide ask form immediately after submission
        askForm.classList.add('hidden');
    });

    answerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const answer = answerInput.value.trim();
        if (!answer) return;
        socket.emit('submit_answer', { answer });
        answerInput.value = '';
        // Hide answer form immediately after submission
        answerForm.classList.add('hidden');
    });

    // --- Socket.IO Handlers ---
    
    function addMessageToLog(message, type = 'normal') {
        const entry = document.createElement('p');
        entry.textContent = message;
        
        // Style based on message type
        switch(type) {
            case 'system':
                entry.style.color = '#666';
                entry.style.fontStyle = 'italic';
                break;
            case 'error':
                entry.style.color = '#d32f2f';
                entry.style.fontWeight = 'bold';
                break;
            case 'success':
                entry.style.color = '#4caf50';
                break;
            default:
                entry.style.color = '#333';
        }
        
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }
    
    // Display welcome message when page loads
    addMessageToLog('👋 Welcome to The Outsider!', 'system');
    addMessageToLog('Type your name below and press "Join" to start playing.', 'system');
    addMessageToLog('The AI is always the Outsider - humans must work together to identify and vote out the AI!', 'system');
    
    socket.on('connect', () => {
        console.log('Connected to server');
        // Join the main room
        socket.emit('join_room', { room: 'main' });
        console.log('Sent join_room event for main room');
        
        // Test the connection
        socket.emit('test', { message: 'Frontend test' });
    });

    socket.on('room_joined', (data) => {
        console.log('Successfully joined room:', data);
        
        // Test room communication
        socket.emit('test_room', { message: 'Testing room communication' });
    });

    socket.on('test_room_response', (data) => {
        console.log('Room communication test response:', data);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
    });

    socket.on('win_counter_update', (data) => {
        console.log('=== WIN COUNTER UPDATE RECEIVED ===');
        console.log('Win counter update data:', data);
        console.log('Current display values - Human:', humanWinsDisplay.textContent, 'AI:', aiWinsDisplay.textContent);
        
        // Update win counter display
        if (data.human_wins !== undefined) {
            humanWinsDisplay.textContent = data.human_wins;
            console.log('Updated human wins to:', data.human_wins);
        }
        if (data.ai_wins !== undefined) {
            aiWinsDisplay.textContent = data.ai_wins;
            console.log('Updated AI wins to:', data.ai_wins);
        }
        
        console.log('Final display values - Human:', humanWinsDisplay.textContent, 'AI:', aiWinsDisplay.textContent);
        console.log('=== WIN COUNTER UPDATE COMPLETE ===');
    });

    socket.on('typing_start', (data) => {
        if (data.username !== myUsername) {
            // Show typing indicator for other players
            const typingEntry = document.createElement('p');
            typingEntry.textContent = `${data.username} is typing...`;
            typingEntry.style.color = '#666';
            typingEntry.style.fontStyle = 'italic';
            typingEntry.style.fontSize = '12px';
            typingEntry.id = `typing-${data.username}`;
            log.appendChild(typingEntry);
            log.scrollTop = log.scrollHeight;
        }
    });

    socket.on('typing_stop', (data) => {
        if (data.username !== myUsername) {
            // Remove typing indicator for other players
            const typingEntry = document.getElementById(`typing-${data.username}`);
            if (typingEntry) {
                typingEntry.remove();
            }
        }
    });

    socket.on('username_taken', (data) => {
        console.log('Username taken error:', data);
        
        // Show error message
        const errorEntry = document.createElement('p');
        errorEntry.textContent = data.message;
        errorEntry.style.color = '#d32f2f';
        errorEntry.style.fontWeight = 'bold';
        log.appendChild(errorEntry);
        log.scrollTop = log.scrollHeight;
        
        // Re-enable the login form so they can try again
        loginForm.classList.remove('hidden');
        gameForms.classList.add('hidden');
        
        // Clear the username input and focus it
        usernameInput.value = '';
        usernameInput.focus();
    });

    socket.on('turn_update', (data) => {
        console.log('=== TURN UPDATE RECEIVED ===');
        console.log('Turn update data:', data);
        console.log('Data type:', typeof data);
        console.log('Data keys:', Object.keys(data));
        console.log('My username:', myUsername);
        console.log('Is my turn to ask:', data.is_my_turn_to_ask);
        console.log('Is my turn to answer:', data.is_my_turn_to_answer);
        console.log('Can ask:', data.can_ask);
        console.log('Can answer:', data.can_answer);
        console.log('Current form states:');
        console.log('- Ask form hidden:', askForm.classList.contains('hidden'));
        console.log('- Answer form hidden:', answerForm.classList.contains('hidden'));
        console.log('- Question input disabled:', questionInput.disabled);
        console.log('- Answer input disabled:', answerInput.disabled);
        
        // Update turn indicator
        if (data.current_asker) {
            if (data.is_my_turn_to_ask) {
                turnIndicator.textContent = `It's your turn to ask a question!`;
                turnIndicator.style.color = '#4caf50';
                console.log('Setting turn indicator to: It\'s your turn to ask a question!');
            } else if (data.is_my_turn_to_answer) {
                turnIndicator.textContent = `${data.current_asker} is asking you a question!`;
                turnIndicator.style.color = '#ff9800';
                console.log('Setting turn indicator to: Someone is asking me a question!');
            } else {
                if (data.current_target) {
                    turnIndicator.textContent = `${data.current_asker} is asking ${data.current_target} a question.`;
                    turnIndicator.style.color = '#666';
                    console.log('Setting turn indicator to: Someone else is asking a question');
                } else {
                    turnIndicator.textContent = `${data.current_asker} is thinking of a question...`;
                    turnIndicator.style.color = '#666';
                    console.log('Setting turn indicator to: Someone is thinking of a question');
                }
            }
        }
        
        // Update form visibility and input restrictions
        if (data.can_ask) {
            console.log('Enabling ask form');
            askForm.classList.remove('hidden');
            answerForm.classList.add('hidden');
            questionInput.disabled = false;
            targetPlayerSelect.disabled = false;
            askBtn.disabled = false;
            
            // Clear any previous answer input
            answerInput.value = '';
        } else if (data.can_answer) {
            console.log('Enabling answer form');
            askForm.classList.add('hidden');
            answerForm.classList.remove('hidden');
            answerInput.disabled = false;
            answerBtn.disabled = false;
            
            // Clear any previous question input
            questionInput.value = '';
        } else {
            console.log('Disabling all forms - not my turn');
            // Not my turn - disable all inputs
            askForm.classList.add('hidden');
            answerForm.classList.add('hidden');
            questionInput.disabled = true;
            targetPlayerSelect.disabled = true;
            askBtn.disabled = true;
            answerInput.disabled = true;
            answerBtn.disabled = true;
            
            // Clear inputs when not my turn
            questionInput.value = '';
            answerInput.value = '';
        }
        
        console.log('=== TURN UPDATE PROCESSING COMPLETE ===');
    });

    socket.on('spectator_turn_update', (data) => {
        console.log('=== SPECTATOR TURN UPDATE RECEIVED ===');
        console.log('Spectator turn update data:', data);
        
        // Only update turn indicator for spectators (don't change forms)
        if (data.current_asker) {
            if (data.current_target) {
                turnIndicator.textContent = `${data.current_asker} is asking ${data.current_target} a question.`;
                turnIndicator.style.color = '#666';
                console.log('Updated spectator turn indicator - question in progress');
            } else {
                turnIndicator.textContent = `${data.current_asker} is thinking of a question...`;
                turnIndicator.style.color = '#666';
                console.log('Updated spectator turn indicator - asker thinking');
            }
        }
        
        console.log('=== SPECTATOR TURN UPDATE PROCESSING COMPLETE ===');
    });

    socket.on('question_asked', (data) => {
        console.log('Question asked:', data);
        console.log('Question data type:', typeof data);
        console.log('Question data keys:', Object.keys(data));
        console.log('Asker:', data.asker);
        console.log('Target:', data.target);
        console.log('Question:', data.question);
        
        // Add question to chat
        const questionEntry = document.createElement('p');
        questionEntry.innerHTML = `<strong>${data.asker}</strong> asks <strong>${data.target}</strong>: ${data.question}`;
        questionEntry.style.color = '#2196f3';
        log.appendChild(questionEntry);
        log.scrollTop = log.scrollHeight;
        
        console.log('Question added to chat');
        
        // Update turn indicator immediately
        if (data.target === myUsername) {
            turnIndicator.textContent = `${data.asker} is asking you a question!`;
            turnIndicator.style.color = '#ff9800';
            
            // Show answer form immediately for the target
            askForm.classList.add('hidden');
            answerForm.classList.remove('hidden');
            answerInput.disabled = false;
            answerBtn.disabled = false;
            answerInput.focus(); // Focus the answer input
        } else {
            turnIndicator.textContent = `${data.asker} is asking ${data.target} a question.`;
            turnIndicator.style.color = '#666';
            
            // Hide all forms for non-target players
            askForm.classList.add('hidden');
            answerForm.classList.add('hidden');
            questionInput.disabled = true;
            answerInput.disabled = true;
            askBtn.disabled = true;
            answerBtn.disabled = true;
        }
    });

    socket.on('ai_question', (data) => {
        console.log('AI question:', data);
        
        // Get AI player name from the target SID
        const aiPlayer = data.target; // This should be the AI's SID
        const aiName = aiPlayer.replace('ai_', ''); // Extract name from SID like "ai_Sam"
        
        // Add AI question to chat
        const questionEntry = document.createElement('p');
        questionEntry.innerHTML = `<strong>${aiName}</strong> asks: ${data.question}`;
        questionEntry.style.color = '#2196f3';
        questionEntry.style.fontStyle = 'italic';
        log.appendChild(questionEntry);
        log.scrollTop = log.scrollHeight;
        
        // Update turn indicator immediately
        if (data.target_sid === myUsername) {
            turnIndicator.textContent = `${aiName} is asking you a question!`;
            turnIndicator.style.color = '#ff9800';
            
            // Show answer form immediately for the target
            askForm.classList.add('hidden');
            answerForm.classList.remove('hidden');
            answerInput.disabled = false;
            answerBtn.disabled = false;
            answerInput.focus(); // Focus the answer input
        } else {
            turnIndicator.textContent = `${aiName} is asking ${data.target} a question.`;
            turnIndicator.style.color = '#666';
            
            // Hide all forms for non-target players
            askForm.classList.add('hidden');
            answerForm.classList.add('hidden');
            questionInput.disabled = true;
            answerInput.disabled = true;
            askBtn.disabled = true;
            answerBtn.disabled = true;
        }
    });

    socket.on('answer_given', (data) => {
        console.log('=== REAL ANSWER GIVEN RECEIVED ===');
        console.log('Answer given:', data);
        console.log('Target:', data.target);
        console.log('Answer:', data.answer);
        console.log('Target SID:', data.target_sid);
        
        // Add answer to chat
        const answerEntry = document.createElement('p');
        answerEntry.innerHTML = `<strong>${data.target}</strong> answers: ${data.answer}`;
        answerEntry.style.color = '#4caf50';
        log.appendChild(answerEntry);
        log.scrollTop = log.scrollHeight;
        
        console.log('Answer added to chat');
        
        // Clear answer form and disable inputs
        answerInput.value = '';
        answerForm.classList.add('hidden');
        answerInput.disabled = true;
        answerBtn.disabled = true;
        
        // Update turn indicator to show waiting for next turn
        turnIndicator.textContent = 'Processing answer...';
        turnIndicator.style.color = '#666';
    });

    socket.on('ai_answer', (data) => {
        console.log('=== AI ANSWER RECEIVED ===');
        console.log('AI answer:', data);
        
        // Add AI answer to chat
        const answerEntry = document.createElement('p');
        answerEntry.innerHTML = `<strong>${data.target}</strong> answers: ${data.answer}`;
        answerEntry.style.color = '#4caf50';
        answerEntry.style.fontStyle = 'italic';
        log.appendChild(answerEntry);
        log.scrollTop = log.scrollHeight;
        
        console.log('AI answer added to chat');
        
        // Clear answer form and disable inputs (in case this player was answering)
        answerInput.value = '';
        answerForm.classList.add('hidden');
        answerInput.disabled = true;
        answerBtn.disabled = true;
        
        // Update turn indicator to show waiting for next turn
        turnIndicator.textContent = 'Processing answer...';
        turnIndicator.style.color = '#666';
    });

    socket.on('location_guess_made', (data) => {
        console.log('Location guess made:', data);
        
        // Add anonymous location guess to chat with appropriate emoji
        const guessEntry = document.createElement('p');
        const emoji = data.is_correct ? "🎯" : "❌";
        guessEntry.innerHTML = `<strong>${emoji} ${data.message}</strong>`;
        guessEntry.style.color = data.is_correct ? '#4caf50' : '#ff9800';
        guessEntry.style.fontWeight = 'bold';
        guessEntry.style.fontSize = '14px';
        log.appendChild(guessEntry);
        log.scrollTop = log.scrollHeight;
        
        console.log('Location guess added to chat');
    });

    socket.on('voting_started', (data) => {
        console.log('Voting started:', data);
        
        // Hide question/answer forms
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        
        // Hide vote request button
        const voteButton = document.getElementById('request-vote-btn');
        if (voteButton) {
            voteButton.style.display = 'none';
        }
        
        // Show voting form
        voteForm.classList.remove('hidden');
        
        // Clear previous vote options
        voteOptions.innerHTML = '';
        selectedVoteTarget = null;
        submitVoteBtn.disabled = true;
        submitVoteBtn.textContent = 'Submit Vote';
        
        // Create vote options
        if (data.players) {
            data.players.forEach(player => {
                if (player.username !== myUsername) { // Can't vote for yourself
                    const option = document.createElement('div');
                    option.className = 'vote-option';
                    option.textContent = player.username;
                    option.dataset.sid = player.sid;
                    option.addEventListener('click', () => {
                        // Remove previous selection
                        document.querySelectorAll('.vote-option').forEach(opt => opt.classList.remove('selected'));
                        option.classList.add('selected');
                        selectedVoteTarget = player.sid;
                        submitVoteBtn.disabled = false;
                        submitVoteBtn.textContent = `Vote for ${player.username}`;
                    });
                    voteOptions.appendChild(option);
                }
            });
            
            // Add Pass option
            const passOption = document.createElement('div');
            passOption.className = 'vote-option';
            passOption.textContent = 'Pass';
            passOption.dataset.sid = 'pass';
            passOption.style.backgroundColor = '#f0f0f0';
            passOption.style.borderColor = '#999';
            passOption.addEventListener('click', () => {
                // Remove previous selection
                document.querySelectorAll('.vote-option').forEach(opt => opt.classList.remove('selected'));
                passOption.classList.add('selected');
                selectedVoteTarget = 'pass';
                submitVoteBtn.disabled = false;
                submitVoteBtn.textContent = 'Pass';
            });
            voteOptions.appendChild(passOption);
        }
        
        // Update turn indicator
        turnIndicator.textContent = '🗳️ Voting Time! Choose who you think is the AI or Pass!';
        turnIndicator.style.color = '#ff9800';
        
        // Add voting message to chat
        const votingEntry = document.createElement('p');
        votingEntry.textContent = '🗳️ Voting has begun! Choose who you think is the AI or Pass!';
        votingEntry.style.fontWeight = 'bold';
        votingEntry.style.color = '#ff9800';
        votingEntry.style.fontSize = '16px';
        log.appendChild(votingEntry);
        log.scrollTop = log.scrollHeight;
    });

    socket.on('question_count_update', (data) => {
        console.log('Question count update:', data);
        
        // Update question counter
        if (data.question_count !== undefined) {
            questionCount.textContent = data.question_count;
        }
        if (data.questions_until_vote !== undefined) {
            if (data.questions_until_vote === 0) {
                if (isSpectator) {
                    questionsUntilVote.textContent = 'Can vote now! (Spectating)';
                    questionsUntilVote.style.cursor = 'default';
                    questionsUntilVote.style.color = '#666';
                    questionsUntilVote.style.fontWeight = 'normal';
                    questionsUntilVote.title = '';
                    questionsUntilVote.onclick = null;
                } else {
                    questionsUntilVote.textContent = 'Can vote now!';
                    questionsUntilVote.style.cursor = 'pointer';
                    questionsUntilVote.style.color = '#ff9800';
                    questionsUntilVote.style.fontWeight = 'bold';
                    questionsUntilVote.title = 'Click to request a vote!';
                    
                    // Add click handler for vote request
                    questionsUntilVote.onclick = () => {
                        console.log('Question counter vote button clicked');
                        socket.emit('request_vote', {});
                        questionsUntilVote.textContent = 'Vote Requested...';
                        questionsUntilVote.style.cursor = 'default';
                        questionsUntilVote.onclick = null;
                    };
                }
            } else {
                questionsUntilVote.textContent = `${data.questions_until_vote} until vote`;
                questionsUntilVote.style.cursor = 'default';
                questionsUntilVote.style.color = '#666';
                questionsUntilVote.style.fontWeight = 'normal';
                questionsUntilVote.title = '';
                questionsUntilVote.onclick = null;
            }
        }
        
        // Hide the separate vote button since we're using the counter
        const voteButton = document.getElementById('request-vote-btn');
        if (voteButton) {
            voteButton.style.display = 'none';
        }
    });

    socket.on('game_ended', (data) => {
        console.log('=== GAME ENDED EVENT RECEIVED ===');
        console.log('Game ended data:', data);
        
        // Hide all game forms
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        voteForm.classList.add('hidden');
        
        // Show game end message
        const gameEndEntry = document.createElement('p');
        gameEndEntry.textContent = data.message;
        gameEndEntry.style.fontWeight = 'bold';
        gameEndEntry.style.color = data.winner === 'humans' ? '#4caf50' : '#d32f2f';
        gameEndEntry.style.fontSize = '16px';
        log.appendChild(gameEndEntry);
        log.scrollTop = log.scrollHeight;
        
        // Update turn indicator
        if (data.message && data.message.includes('correctly guessed the location')) {
            turnIndicator.textContent = '🎯 AI Wins by Location Guess!';
            turnIndicator.style.color = '#d32f2f';
        } else {
            turnIndicator.textContent = `Game Over! ${data.winner === 'humans' ? 'Humans Win!' : 'AI Wins!'}`;
            turnIndicator.style.color = data.winner === 'humans' ? '#4caf50' : '#d32f2f';
        }
        
        console.log('Game ended UI updated - waiting for reset...');
    });

    socket.on('voting_results', (data) => {
        console.log('Voting results:', data);
        
        // Add voting results message to chat
        const resultsEntry = document.createElement('p');
        resultsEntry.textContent = data.message;
        resultsEntry.style.fontWeight = 'bold';
        resultsEntry.style.color = '#ff9800';
        resultsEntry.style.fontSize = '14px';
        log.appendChild(resultsEntry);
        log.scrollTop = log.scrollHeight;
        
        // Handle all passed scenario
        if (data.all_passed) {
            // Hide voting form and show game forms again
            voteForm.classList.add('hidden');
            askForm.classList.remove('hidden');
            answerForm.classList.add('hidden');
            
            // Restore vote button functionality if enough questions have been asked
            if (!isSpectator) {
                questionsUntilVote.textContent = 'Can vote now!';
                questionsUntilVote.style.cursor = 'pointer';
                questionsUntilVote.style.color = '#ff9800';
                questionsUntilVote.style.fontWeight = 'bold';
                questionsUntilVote.title = 'Click to request a vote!';
                
                // Add click handler for vote request
                questionsUntilVote.onclick = () => {
                    console.log('Question counter vote button clicked');
                    socket.emit('request_vote', {});
                    questionsUntilVote.textContent = 'Vote Requested...';
                    questionsUntilVote.style.cursor = 'default';
                    questionsUntilVote.onclick = null;
                };
            }
            
            // Update turn indicator
            turnIndicator.textContent = '🤝 Everyone passed! Game continues...';
            turnIndicator.style.color = '#4caf50';
        }
    });

    socket.on('spectator_mode', (data) => {
        console.log('Entering spectator mode:', data);
        isSpectator = true;
        
        // Update UI for spectator mode
        myRole.textContent = "You are a Spectator";
        myRole.style.fontWeight = 'bold';
        myRole.style.color = '#666';
        myLocation.textContent = "Location: ???";
        myLocation.style.color = '#666';
        
        startGameBtn.classList.add('hidden');
        questionCounter.classList.remove('hidden');
        
        // Hide interactive elements for spectators
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        voteForm.classList.add('hidden');
        
        // Hide vote request button for spectators
        const voteButton = document.getElementById('request-vote-btn');
        if (voteButton) {
            voteButton.style.display = 'none';
        }
        
        // Show spectator message
        turnIndicator.textContent = "👁️ Spectating - Watch the game!";
        turnIndicator.style.color = '#666';
        
        // Update question counter
        if (data.question_count !== undefined) {
            questionCount.textContent = data.question_count;
        }
        if (data.questions_until_vote !== undefined) {
            if (data.questions_until_vote === 0) {
                questionsUntilVote.textContent = 'Can vote now! (Spectating)';
                questionsUntilVote.style.cursor = 'default';
                questionsUntilVote.style.color = '#666';
                questionsUntilVote.style.fontWeight = 'normal';
                questionsUntilVote.title = '';
                questionsUntilVote.onclick = null;
            } else {
                questionsUntilVote.textContent = `${data.questions_until_vote} until vote`;
                questionsUntilVote.style.cursor = 'default';
                questionsUntilVote.style.color = '#666';
                questionsUntilVote.style.fontWeight = 'normal';
                questionsUntilVote.title = '';
                questionsUntilVote.onclick = null;
            }
        }
        
        // Add spectator message to log
        const spectatorEntry = document.createElement('p');
        spectatorEntry.textContent = data.message;
        spectatorEntry.style.fontStyle = 'italic';
        spectatorEntry.style.color = '#666';
        log.appendChild(spectatorEntry);
        log.scrollTop = log.scrollHeight;
    });

    socket.on('game_started', (data) => {
        console.log('=== GAME STARTED EVENT RECEIVED ===');
        console.log('Game started with data:', data);
        console.log('Data type:', typeof data);
        console.log('Data keys:', Object.keys(data));
        console.log('Location:', data.location);
        console.log('Players:', data.players);
        console.log('Current UI state:');
        console.log('- Login form hidden:', loginForm.classList.contains('hidden'));
        console.log('- Game forms hidden:', gameForms.classList.contains('hidden'));
        console.log('- myUsername:', myUsername);
        
        isSpectator = false;
        
        // Show username instead of role (use stored myUsername)
        myRole.textContent = `You are: ${myUsername}`;
        myRole.style.fontWeight = 'bold';
        myRole.style.color = '#2196f3';
        
        // Show location to all humans (since they're all Insiders)
        myLocation.textContent = `Location: ${data.location}`;
        myLocation.style.color = '#4caf50';
        
        startGameBtn.classList.add('hidden');
        questionCounter.classList.remove('hidden');
        questionCount.textContent = '0';
        questionsUntilVote.textContent = '5 until vote';
        questionsUntilVote.style.cursor = 'default';
        questionsUntilVote.style.color = '#666';
        questionsUntilVote.style.fontWeight = 'normal';
        questionsUntilVote.title = '';
        questionsUntilVote.onclick = null;
        
        // Initially disable all inputs until turn_update is received
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        questionInput.disabled = true;
        targetPlayerSelect.disabled = true;
        askBtn.disabled = true;
        answerInput.disabled = true;
        answerBtn.disabled = true;
        
        // Hide vote request button initially
        const voteButton = document.getElementById('request-vote-btn');
        if (voteButton) {
            voteButton.style.display = 'none';
        }
        
        // Set initial turn indicator
        turnIndicator.textContent = 'Waiting for first question...';
        turnIndicator.style.color = '#666';
    });

    socket.on('game_over', (data) => {
        console.log('Game over:', data);
        
        // Hide game forms
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        
        // Show game over message
        let gameOverMessage = '';
        if (data.win_reason === 'outsider_guess') {
            gameOverMessage = `🎉 ${data.winner} correctly guessed the location! The location was ${data.actual_location}. The Outsider wins!`;
        }
        
        const gameOverEntry = document.createElement('p');
        gameOverEntry.style.fontWeight = 'bold';
        gameOverEntry.style.color = '#d32f2f';
        gameOverEntry.style.fontSize = '16px';
        gameOverEntry.textContent = gameOverMessage;
        log.appendChild(gameOverEntry);
        log.scrollTop = log.scrollHeight;
        
        // Update turn indicator
        turnIndicator.textContent = 'Game Over!';
        turnIndicator.style.color = '#d32f2f';
        
        // Show restart option
        const restartBtn = document.createElement('button');
        restartBtn.textContent = 'Play Again';
        restartBtn.style.marginTop = '10px';
        restartBtn.addEventListener('click', () => {
            location.reload();
        });
        document.getElementById('input-area').appendChild(restartBtn);
    });

    socket.on('game_reset', (data) => {
        console.log('=== GAME RESET EVENT RECEIVED ===');
        console.log('Game reset data:', data);
        console.log('Current UI state before reset:');
        console.log('- Login form hidden:', loginForm.classList.contains('hidden'));
        console.log('- Game forms hidden:', gameForms.classList.contains('hidden'));
        console.log('- myUsername:', myUsername);
        
        // Reset UI to initial state
        myRole.textContent = 'Waiting...';
        myRole.style.fontWeight = 'normal';
        myRole.style.color = 'inherit';
        myLocation.textContent = 'Location: ???';
        myLocation.style.color = 'inherit';
        
        // Show login form again
        loginForm.classList.remove('hidden');
        gameForms.classList.add('hidden');
        
        // Clear player list
        playerList.innerHTML = '';
        
        // Hide question counter and voting form
        questionCounter.classList.add('hidden');
        voteForm.classList.add('hidden');
        
        // Reset turn indicator
        turnIndicator.textContent = 'Game reset! Enter your name to join a new game.';
        turnIndicator.style.color = '#2196f3';
        
        // Clear all forms
        questionInput.value = '';
        answerInput.value = '';
        usernameInput.value = '';
        
        // Reset spectator status
        isSpectator = false;
        
        // Reset myUsername so they can enter a new name
        myUsername = null;
        
        // Add reset message to log
        const resetEntry = document.createElement('p');
        resetEntry.textContent = data.message;
        resetEntry.style.fontWeight = 'bold';
        resetEntry.style.color = '#2196f3';
        resetEntry.style.fontSize = '16px';
        log.appendChild(resetEntry);
        log.scrollTop = log.scrollHeight;
        
        // Add instruction message
        const instructionEntry = document.createElement('p');
        instructionEntry.textContent = 'Enter your name above to join a new game!';
        instructionEntry.style.fontStyle = 'italic';
        instructionEntry.style.color = '#666';
        instructionEntry.style.fontSize = '14px';
        log.appendChild(instructionEntry);
        log.scrollTop = log.scrollHeight;
        
        // Focus username input for new game
        usernameInput.focus();
        
        // Reset question counter styling
        questionsUntilVote.textContent = '5 until vote';
        questionsUntilVote.style.cursor = 'default';
        questionsUntilVote.style.color = '#666';
        questionsUntilVote.style.fontWeight = 'normal';
        questionsUntilVote.title = '';
        questionsUntilVote.onclick = null;
        
        // Reset win counter display (only for manual reset)
        if (data.message && data.message.includes('Manual reset')) {
            humanWinsDisplay.textContent = '0';
            aiWinsDisplay.textContent = '0';
        }
        
        // Hide all game forms
        askForm.classList.add('hidden');
        answerForm.classList.add('hidden');
        voteForm.classList.add('hidden');
        
        // Hide vote request button
        const voteButton = document.getElementById('request-vote-btn');
        if (voteButton) {
            voteButton.style.display = 'none';
        }
        
        console.log('Game reset completed - ready for new players');
        console.log('- Login form hidden after reset:', loginForm.classList.contains('hidden'));
        console.log('- Game forms hidden after reset:', gameForms.classList.contains('hidden'));
    });

    socket.on('game_update', (data) => {
        console.log('=== GAME UPDATE RECEIVED ===');
        console.log('Game update received:', data);
        console.log('Data type:', typeof data);
        console.log('Data keys:', Object.keys(data));
        
        // Check for error responses (like username taken)
        if (data.error) {
            console.log('Error in game update:', data.log);
            
            // Show error message
            const errorEntry = document.createElement('p');
            errorEntry.textContent = data.log;
            errorEntry.style.color = '#d32f2f';
            errorEntry.style.fontWeight = 'bold';
            log.appendChild(errorEntry);
            log.scrollTop = log.scrollHeight;
            
            // If it's a username taken error, re-enable the login form
            if (data.log && data.log.includes('already taken')) {
                loginForm.classList.remove('hidden');
                gameForms.classList.add('hidden');
                
                // Clear the username input and focus it
                usernameInput.value = '';
                usernameInput.focus();
            }
            
            return; // Don't process other updates for errors
        }
        
        // Update start game button visibility
        if (data.can_start_game !== undefined) {
            console.log('can_start_game:', data.can_start_game);
            if (data.can_start_game && !isSpectator) {
                startGameBtn.classList.remove('hidden');
                startGameBtn.disabled = false;
                console.log('Start game button shown');
            } else {
                startGameBtn.classList.add('hidden');
                startGameBtn.disabled = true;
                console.log('Start game button hidden');
            }
        }
        
        // Update question counter
        if (data.question_count !== undefined) {
            questionCount.textContent = data.question_count;
        }
        if (data.questions_until_vote !== undefined) {
            if (data.questions_until_vote === 0) {
                if (isSpectator) {
                    questionsUntilVote.textContent = 'Can vote now! (Spectating)';
                    questionsUntilVote.style.cursor = 'default';
                    questionsUntilVote.style.color = '#666';
                    questionsUntilVote.style.fontWeight = 'normal';
                    questionsUntilVote.title = '';
                    questionsUntilVote.onclick = null;
                } else {
                    questionsUntilVote.textContent = 'Can vote now!';
                    questionsUntilVote.style.cursor = 'pointer';
                    questionsUntilVote.style.color = '#ff9800';
                    questionsUntilVote.style.fontWeight = 'bold';
                    questionsUntilVote.title = 'Click to request a vote!';
                    
                    // Add click handler for vote request
                    questionsUntilVote.onclick = () => {
                        console.log('Question counter vote button clicked');
                        socket.emit('request_vote', {});
                        questionsUntilVote.textContent = 'Vote Requested...';
                        questionsUntilVote.style.cursor = 'default';
                        questionsUntilVote.onclick = null;
                    };
                }
            } else {
                questionsUntilVote.textContent = `${data.questions_until_vote} until vote`;
                questionsUntilVote.style.cursor = 'default';
                questionsUntilVote.style.color = '#666';
                questionsUntilVote.style.fontWeight = 'normal';
                questionsUntilVote.title = '';
                questionsUntilVote.onclick = null;
            }
        }
        
        // Handle voting mode
        if (data.mode === 'voting') {
            console.log('Entering voting mode');
            if (!isSpectator) {
                askForm.classList.add('hidden');
                answerForm.classList.add('hidden');
                voteForm.classList.remove('hidden');
                
                // Clear previous vote options
                voteOptions.innerHTML = '';
                selectedVoteTarget = null;
                submitVoteBtn.disabled = true;
                submitVoteBtn.textContent = 'Submit Vote';
                
                // Create vote options
                if (data.voting_players) {
                    data.voting_players.forEach(player => {
                        if (player.username !== myUsername) { // Can't vote for yourself
                            const option = document.createElement('div');
                            option.className = 'vote-option';
                            option.textContent = player.username;
                            option.dataset.sid = player.sid;
                            option.addEventListener('click', () => {
                                // Remove previous selection
                                document.querySelectorAll('.vote-option').forEach(opt => {
                                    opt.classList.remove('selected');
                                });
                                // Select this option
                                option.classList.add('selected');
                                selectedVoteTarget = player.sid;
                                submitVoteBtn.disabled = false;
                            });
                            voteOptions.appendChild(option);
                        }
                    });
                    
                    // Add Pass option
                    const passOption = document.createElement('div');
                    passOption.className = 'vote-option';
                    passOption.textContent = 'Pass';
                    passOption.dataset.sid = 'pass';
                    passOption.style.backgroundColor = '#f0f0f0';
                    passOption.style.borderColor = '#999';
                    passOption.addEventListener('click', () => {
                        // Remove previous selection
                        document.querySelectorAll('.vote-option').forEach(opt => {
                            opt.classList.remove('selected');
                        });
                        // Select this option
                        passOption.classList.add('selected');
                        selectedVoteTarget = 'pass';
                        submitVoteBtn.disabled = false;
                    });
                    voteOptions.appendChild(passOption);
                }
            } else {
                // Spectators see voting but can't participate
                turnIndicator.textContent = "🗳️ Voting in progress... (Spectating)";
            }
        } else if (data.mode === 'asking') {
            // Turn system is handled by turn_update events
            // This is just for mode indication
        } else if (data.mode === 'answering') {
            // Turn system is handled by turn_update events
            // This is just for mode indication
        }
        
        // Update player list
        if (data.players) {
            console.log('=== UPDATING PLAYER LIST ===');
            console.log('Updating player list with:', data.players);
            console.log('Player list type:', Array.isArray(data.players));
            console.log('My username:', myUsername);
            console.log('Is spectator:', isSpectator);
            playerList.innerHTML = '';
            targetPlayerSelect.innerHTML = '';
            
            data.players.forEach(player => {
                console.log('Adding player to list:', player);
                const li = document.createElement('li');
                li.textContent = player;
                playerList.appendChild(li);

                // Add to dropdown for asking questions, but don't let players ask themselves
                if (player !== myUsername && !isSpectator) {
                    const option = document.createElement('option');
                    option.value = player;
                    option.textContent = player;
                    targetPlayerSelect.appendChild(option);
                    console.log('Added target option:', player);
                } else {
                    console.log('Skipping target option for:', player, '(self or spectator)');
                }
            });
            console.log('Player list updated, current HTML:', playerList.innerHTML);
            console.log('Target dropdown options:', Array.from(targetPlayerSelect.options).map(opt => opt.value));
        } else {
            console.log('No players data in game_update');
        }
        
        // Add new log entry
        if (data.log) {
            console.log('Adding log entry:', data.log);
            const entry = document.createElement('p');
            entry.textContent = data.log;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight; // Auto-scroll
        }
        
        // Update turn indicator based on current asker/target
        if (data.current_asker) {
            if (data.current_target) {
                if (data.current_target === myUsername) {
                    turnIndicator.textContent = `${data.current_asker} is asking you a question!`;
                    turnIndicator.style.color = '#ff9800';
                } else {
                    turnIndicator.textContent = `${data.current_asker} is asking ${data.current_target} a question.`;
                    turnIndicator.style.color = '#666';
                }
            } else {
                if (data.current_asker === myUsername) {
                    turnIndicator.textContent = `It's your turn to ask a question!`;
                    turnIndicator.style.color = '#4caf50';
                } else {
                    turnIndicator.textContent = `It's ${data.current_asker}'s turn to ask a question.`;
                    turnIndicator.style.color = '#666';
                }
            }
        }

        // Handle vote results
        if (data.vote_result) {
            if (data.vote_result === 'humans_win') {
                turnIndicator.textContent = `🎉 Game Over - Humans Win!`;
                askForm.classList.add('hidden');
                answerForm.classList.add('hidden');
                voteForm.classList.add('hidden');
            } else if (data.vote_result === 'ai_wins') {
                turnIndicator.textContent = `🤖 Game Over - AI Wins!`;
                askForm.classList.add('hidden');
                answerForm.classList.add('hidden');
                voteForm.classList.add('hidden');
            } else if (data.vote_result === 'tie_elimination') {
                turnIndicator.textContent = `🤝 Tie! Both players eliminated!`;
            } else if (data.vote_result === 'innocent_eliminated') {
                turnIndicator.textContent = `❌ ${data.eliminated_player} was eliminated!`;
            } else if (data.vote_result === 'tie') {
                turnIndicator.textContent = `🤝 It's a tie! No one eliminated.`;
            }
        }
    });

    console.log('Event listeners and Socket.IO handlers set up successfully');
});