package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
	"unicode"
)

const (
	defaultBaseURL = "http://localhost:8008"
	defaultLimit   = 5
)

type newsItem struct {
	Title          string  `json:"title"`
	URL            string  `json:"url"`
	Source         string  `json:"source"`
	PublishedAt    string  `json:"published_at"`
	Summary        string  `json:"summary"`
	Sentiment      string  `json:"sentiment"`
	SentimentScore float64 `json:"sentiment_score"`
	Excerpt        string  `json:"excerpt"`
}

type apiError struct {
	Error  string `json:"error"`
	Detail string `json:"detail"`
}

type agentClient struct {
	baseURL    string
	httpClient *http.Client
}

func newAgentClient(baseURL string, timeout time.Duration) *agentClient {
	if baseURL == "" {
		baseURL = defaultBaseURL
	}
	return &agentClient{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

func (c *agentClient) Query(ctx context.Context, query string, limit int) ([]newsItem, error) {
	payload := map[string]any{
		"query": query,
	}
	if limit > 0 {
		payload["limit"] = limit
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	endpoint := c.baseURL + "/news"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		var apiErr apiError
		if err := json.Unmarshal(data, &apiErr); err == nil && apiErr.Error != "" {
			msg := apiErr.Error
			if apiErr.Detail != "" {
				msg += ": " + apiErr.Detail
			}
			return nil, errors.New(msg)
		}
		return nil, fmt.Errorf("agent returned status %s", resp.Status)
	}

	var items []newsItem
	if err := json.Unmarshal(data, &items); err != nil {
		return nil, err
	}
	return items, nil
}

func main() {
	baseURL := flag.String("base", envOrDefault("NEWS_AGENT_BASE_URL", defaultBaseURL), "news agent base URL")
	limit := flag.Int("limit", defaultLimit, "maximum articles to request per query")
	timeout := flag.Duration("timeout", 10*time.Second, "HTTP client timeout")
	flag.Parse()

	client := newAgentClient(*baseURL, *timeout)
	reader := bufio.NewScanner(os.Stdin)

	fmt.Printf("News Agent CLI connected to %s\n", client.baseURL)
	fmt.Println("Type your query and press enter. Type 'exit' or 'quit' to leave.")

	for {
		fmt.Print("\n> ")
		if !reader.Scan() {
			fmt.Println()
			break
		}
		query := strings.TrimSpace(reader.Text())
		if query == "" {
			continue
		}
		if strings.EqualFold(query, "exit") || strings.EqualFold(query, "quit") {
			break
		}

		ctx, cancel := context.WithTimeout(context.Background(), *timeout)
		items, err := client.Query(ctx, query, *limit)
		cancel()
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}
		if len(items) == 0 {
			fmt.Println("No articles found.")
			continue
		}
		for idx, item := range items {
			fmt.Printf("\n[%d] %s\n", idx+1, item.Title)
			fmt.Printf("    Source: %s\n", item.Source)
			if published := formatPublished(item.PublishedAt); published != "" {
				fmt.Printf("    Published: %s\n", published)
			}
			fmt.Printf("    Sentiment: %s (%.2f)\n", formatSentiment(item.Sentiment), item.SentimentScore)
			if item.Summary != "" {
				fmt.Printf("    Summary: %s\n", item.Summary)
			} else if item.Excerpt != "" {
				fmt.Printf("    Excerpt: %s\n", item.Excerpt)
			}
			if item.URL != "" {
				fmt.Printf("    URL: %s\n", item.URL)
			}
		}
	}
}

func formatPublished(value string) string {
	if value == "" {
		return ""
	}
	parsed, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return value
	}
	return parsed.Local().Format(time.RFC1123)
}

func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func formatSentiment(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "Unknown"
	}
	runes := []rune(value)
	runes[0] = unicode.ToUpper(runes[0])
	for i := 1; i < len(runes); i++ {
		runes[i] = unicode.ToLower(runes[i])
	}
	return string(runes)
}
