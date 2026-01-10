import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IndicatorContribution } from '@/components/analysis/IndicatorContribution'

describe('IndicatorContribution', () => {
  const mockContributions = [
    { name: 'RSI', score: 80, weight: 30 },
    { name: 'MACD', score: 20, weight: 20 },
    { name: 'Volume', score: 50, weight: 15 },
  ]

  it('renders all contributions', () => {
    render(<IndicatorContribution contributions={mockContributions} />)
    
    expect(screen.getByText('RSI')).toBeInTheDocument()
    expect(screen.getByText('MACD')).toBeInTheDocument()
    expect(screen.getByText('Volume')).toBeInTheDocument()
    
    expect(screen.getByText('80')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
  })

  it('displays weights correctly', () => {
    render(<IndicatorContribution contributions={mockContributions} />)
    
    expect(screen.getByText('가중치 30%')).toBeInTheDocument()
    expect(screen.getByText('가중치 20%')).toBeInTheDocument()
    expect(screen.getByText('가중치 15%')).toBeInTheDocument()
  })

  it('applies correct colors based on score', () => {
    render(<IndicatorContribution contributions={mockContributions} />)
    
    const rsiScore = screen.getByText('80')
    expect(rsiScore).toHaveClass('text-green-600')
    
    const macdScore = screen.getByText('20')
    expect(macdScore).toHaveClass('text-red-600')
    
    const volumeScore = screen.getByText('50')
    expect(volumeScore).toHaveClass('text-yellow-600')
  })
})
